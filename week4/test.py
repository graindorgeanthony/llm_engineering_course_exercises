def add(a, b):
    """
    Returns the sum of two numbers.

    :param a: The first number.
    :param b: The second number.
    :return: The sum of a and b.
    """
    return a + b


def multiply(a, b):
    """
    Returns the product of two numbers.

    :param a: The first number.
    :param b: The second number.
    :return: The product of a and b.
    """
    return a * b


def main():
    """
    Executes the main logic of the script by performing addition
    and multiplication on sample values.
    """
    # Initialize sample integer values
    x = 3
    y = 7
    
    # Perform and display addition
    print(add(x, y))
    
    # Perform and display multiplication
    print(multiply(x, y))


if __name__ == "__main__":
    # Standard entry point for the script
    main()
