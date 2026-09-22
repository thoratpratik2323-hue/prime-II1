def calculator():
    print("Simple Python Calculator")
    print("Select operation:")
    print("1. Add (+)")
    print("2. Subtract (-)")
    print("3. Multiply (*)")
    print("4. Divide (/)")

    while True:
        choice = input("Enter choice (1/2/3/4) or 'q' to quit: ")
        
        if choice.lower() == 'q':
            print("Exiting calculator. Goodbye!")
            break

        if choice in ('1', '2', '3', '4'):
            try:
                num1 = float(input("Enter first number: "))
                num2 = float(input("Enter second number: "))
            except ValueError:
                print("Invalid input. Please enter numbers only.")
                continue

            if choice == '1':
                print(f"Result: {num1} + {num2} = {num1 + num2}\n")
            elif choice == '2':
                print(f"Result: {num1} - {num2} = {num1 - num2}\n")
            elif choice == '3':
                print(f"Result: {num1} * {num2} = {num1 * num2}\n")
            elif choice == '4':
                if num2 == 0.0:
                    print("Error: Division by zero is not allowed.\n")
                else:
                    print(f"Result: {num1} / {num2} = {num1 / num2}\n")
        else:
            print("Invalid input. Please select a valid option.\n")

if __name__ == "__main__":
    calculator()
