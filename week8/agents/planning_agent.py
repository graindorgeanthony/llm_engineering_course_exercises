"""
Planning Agent - Coordinates activities across all agents using LangGraph
"""
from typing import List, Optional, TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from models import Deal, Opportunity, DealSelection
from agents.scanner_agent import ScannerAgent
from agents.rag_pricer_agent import EnsemblePricerAgent
from agents.messaging_agent import MessagingAgent
from utils import BaseAgent, GREEN
import operator


class PlanningState(TypedDict):
    """State for the planning agent workflow"""
    memory: List[Opportunity]
    scanned_deals: Optional[DealSelection]
    opportunities: List[Opportunity]
    best_opportunity: Optional[Opportunity]
    messages: Annotated[List, operator.add]
    error: Optional[str]


class PlanningAgent(BaseAgent):
    """
    Planning Agent coordinates the workflow using LangGraph
    """
    name = "Planning Agent"
    color = GREEN
    DEAL_THRESHOLD = 50.0  # Minimum discount to trigger notification
    
    def __init__(
        self,
        scanner: ScannerAgent,
        pricer: EnsemblePricerAgent,
        messenger: MessagingAgent
    ):
        """
        Initialize the Planning Agent with sub-agents
        
        Args:
            scanner: Scanner agent for finding deals
            pricer: Ensemble pricer agent for estimating prices
            messenger: Messaging agent for notifications
        """
        self.log("Planning Agent is initializing")
        
        self.scanner = scanner
        self.pricer = pricer
        self.messenger = messenger
        
        # Build the workflow graph
        self._build_graph()
        
        self.log("Planning Agent is ready")
    
    def _build_graph(self):
        """
        Build the LangGraph workflow
        """
        # Create workflow graph
        workflow = StateGraph(PlanningState)
        
        # Add nodes
        workflow.add_node("scan", self._scan_node)
        workflow.add_node("price", self._price_node)
        workflow.add_node("evaluate", self._evaluate_node)
        workflow.add_node("notify", self._notify_node)
        
        # Set entry point
        workflow.set_entry_point("scan")
        
        # Add edges
        workflow.add_conditional_edges(
            "scan",
            self._should_continue_after_scan,
            {
                "price": "price",
                "end": END
            }
        )
        
        workflow.add_edge("price", "evaluate")
        
        workflow.add_conditional_edges(
            "evaluate",
            self._should_notify,
            {
                "notify": "notify",
                "end": END
            }
        )
        
        workflow.add_edge("notify", END)
        
        # Compile the graph
        self.graph = workflow.compile()
        
        self.log("Workflow graph compiled successfully")
    
    def _scan_node(self, state: PlanningState) -> PlanningState:
        """
        Scan for new deals
        """
        self.log("Scanning for new deals")
        
        try:
            scanned_deals = self.scanner.scan(memory=state["memory"])
            state["scanned_deals"] = scanned_deals
            state["messages"].append(HumanMessage(content="Scanning completed"))
            
            if scanned_deals:
                self.log(f"Found {len(scanned_deals.deals)} promising deals")
            else:
                self.log("No new deals found")
                
        except Exception as e:
            self.log(f"Error during scanning: {e}")
            state["error"] = str(e)
            state["scanned_deals"] = None
        
        return state
    
    def _price_node(self, state: PlanningState) -> PlanningState:
        """
        Price all scanned deals
        """
        self.log("Pricing scanned deals")
        
        opportunities = []
        scanned_deals = state["scanned_deals"]
        
        if scanned_deals:
            for deal in scanned_deals.deals[:5]:  # Process top 5
                try:
                    self.log(f"Pricing: {deal.product_description[:50]}...")
                    
                    # Get price estimate
                    estimate = self.pricer.price(deal.product_description)
                    discount = estimate - deal.price
                    
                    opportunity = Opportunity(
                        deal=deal,
                        estimate=estimate,
                        discount=discount
                    )
                    
                    opportunities.append(opportunity)
                    
                    self.log(f"Price: ${deal.price:.2f}, Estimate: ${estimate:.2f}, Discount: ${discount:.2f}")
                    
                except Exception as e:
                    self.log(f"Error pricing deal: {e}")
                    continue
        
        state["opportunities"] = opportunities
        state["messages"].append(HumanMessage(content=f"Priced {len(opportunities)} deals"))
        
        return state
    
    def _evaluate_node(self, state: PlanningState) -> PlanningState:
        """
        Evaluate opportunities and select the best one
        """
        self.log("Evaluating opportunities")
        
        opportunities = state["opportunities"]
        
        if opportunities:
            # Sort by discount
            opportunities.sort(key=lambda opp: opp.discount, reverse=True)
            best = opportunities[0]
            
            state["best_opportunity"] = best
            self.log(f"Best opportunity has ${best.discount:.2f} discount")
            
            state["messages"].append(
                HumanMessage(content=f"Best deal: ${best.discount:.2f} discount")
            )
        else:
            state["best_opportunity"] = None
            self.log("No opportunities to evaluate")
        
        return state
    
    def _notify_node(self, state: PlanningState) -> PlanningState:
        """
        Send notification for the best opportunity
        """
        self.log("Sending notification")
        
        best = state["best_opportunity"]
        
        if best:
            try:
                self.messenger.alert(best)
                state["messages"].append(
                    AIMessage(content=f"Notification sent for ${best.discount:.2f} deal")
                )
            except Exception as e:
                self.log(f"Error sending notification: {e}")
                state["error"] = str(e)
        
        return state
    
    def _should_continue_after_scan(self, state: PlanningState) -> str:
        """
        Decide whether to continue after scanning
        """
        if state["scanned_deals"] and len(state["scanned_deals"].deals) > 0:
            return "price"
        return "end"
    
    def _should_notify(self, state: PlanningState) -> str:
        """
        Decide whether to send notification
        """
        best = state["best_opportunity"]
        
        if best and best.discount > self.DEAL_THRESHOLD:
            return "notify"
        
        if best:
            self.log(f"Discount ${best.discount:.2f} below threshold ${self.DEAL_THRESHOLD:.2f}")
        
        return "end"
    
    def plan(self, memory: List[Opportunity] = []) -> Optional[Opportunity]:
        """
        Execute the full planning workflow
        
        Args:
            memory: List of previously processed opportunities
            
        Returns:
            Best opportunity if found, otherwise None
        """
        self.log("Starting planning workflow")
        
        # Initialize state
        initial_state: PlanningState = {
            "memory": memory,
            "scanned_deals": None,
            "opportunities": [],
            "best_opportunity": None,
            "messages": [],
            "error": None
        }
        
        # Run the workflow
        try:
            final_state = self.graph.invoke(initial_state)
            
            best = final_state.get("best_opportunity")
            
            if best and best.discount > self.DEAL_THRESHOLD:
                self.log(f"Planning completed successfully - best deal: ${best.discount:.2f}")
                return best
            else:
                self.log("Planning completed - no deals above threshold")
                return None
                
        except Exception as e:
            self.log(f"Error in planning workflow: {e}")
            return None
    
    def run_single_deal(self, deal: Deal) -> Opportunity:
        """
        Process a single deal (for testing)
        
        Args:
            deal: The deal to process
            
        Returns:
            Opportunity with price estimate
        """
        self.log("Processing single deal")
        
        estimate = self.pricer.price(deal.product_description)
        discount = estimate - deal.price
        
        opportunity = Opportunity(
            deal=deal,
            estimate=estimate,
            discount=discount
        )
        
        self.log(f"Deal processed - discount: ${discount:.2f}")
        
        return opportunity
