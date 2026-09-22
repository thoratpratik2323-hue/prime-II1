def reverse_string(s: str) -> str:
    """Reverses the input string using slicing."""
    return s[::-1]

# Example usage
test_str = "Prime Cockpit"
reversed_str = reverse_string(test_str)
print(f"Original: {test_str}")
print(f"Reversed: {reversed_str}")
