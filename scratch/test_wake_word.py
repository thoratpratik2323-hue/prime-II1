"""
Test wake word detection and sentence filtering in Prime AI.
Ensures Prime NEVER acts unless 'prime' is explicitly spoken in the sentence.
"""
import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_assistant import clean_command, REQUIRE_WAKE_WORD, WAKE_WORDS, get_require_wake_word, set_require_wake_word

def run_tests():
    print("=" * 60)
    print("TESTING PRIME WAKE WORD ENFORCEMENT")
    print(f"REQUIRE_WAKE_WORD active: {get_require_wake_word()}")
    print(f"WAKE_WORDS: {WAKE_WORDS}")
    print("=" * 60)

    # Ensure wake word is required
    set_require_wake_word(True)

    test_cases = [
        # (Spoken text, Expected should_run, Expected command_contains or exact)
        ("Prime open YouTube", True, "open youtube"),
        ("open YouTube Prime", True, "open youtube"),
        ("Prime", True, ""),
        ("Hey Prime what is the CPU usage", True, "what is the cpu usage"),
        ("OK Prime Pune weather batao", True, "pune weather batao"),
        ("Suno Prime volume badhao", True, "volume badhao"),
        ("bhai Prime chrome open karo", True, "bhai chrome open karo"),
        ("Hello Prime", True, ""),
        ("IP Prime system status", True, "system status"),
        ("Oye Prime gaana bajao", True, "gaana bajao"),
        
        # Sentences WITHOUT 'prime' - MUST ALL BE REJECTED (should_run=False)
        ("open YouTube", False, None),
        ("kya kar rahe ho", False, None),
        ("weather kaisa hai", False, None),
        ("bro open notepad", False, None),
        ("buddy what time is it", False, None),
        ("jarvis open chrome", False, None),
        ("computer shut down", False, None),
        ("tum kahan ja rahe ho", False, None),
        ("primary school", False, None),
        ("primal instinct", False, None),
        ("imprime", False, None),
    ]

    passed = 0
    failed = 0

    for spoken, expected_run, expected_cmd in test_cases:
        should_run, cmd = clean_command(spoken)
        
        ok = (should_run == expected_run)
        if ok and expected_run and expected_cmd is not None:
            ok = (cmd.strip() == expected_cmd.strip())
            
        if ok:
            passed += 1
            status = "PASS"
            print(f"  [{status}] Spoken: \"{spoken}\" -> should_run={should_run}, cmd=\"{cmd}\"")
        else:
            failed += 1
            status = "FAIL"
            print(f"  [{status}] Spoken: \"{spoken}\" -> Expected: run={expected_run}, cmd=\"{expected_cmd}\" | Got: run={should_run}, cmd=\"{cmd}\"")

    print("=" * 60)
    print(f"RESULTS: {passed}/{len(test_cases)} PASSED ({(passed/len(test_cases))*100:.0f}%)")
    if failed == 0:
        print("ALL TESTS PASSED! Prime will strictly ONLY trigger when 'Prime' is spoken.")
    else:
        print(f"FAILED: {failed} tests failed.")
    print("=" * 60)
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
