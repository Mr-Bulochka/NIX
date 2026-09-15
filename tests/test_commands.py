import unittest
from nix.commands import COMMANDS, get_command, CommandResult


class TestCommands(unittest.TestCase):
    def test_all_commands_registered(self):
        self.assertIn("help", COMMANDS)
        self.assertIn("status", COMMANDS)
        self.assertIn("scan", COMMANDS)
        self.assertIn("attempts", COMMANDS)
        self.assertIn("pet", COMMANDS)
        self.assertIn("mode", COMMANDS)
        self.assertIn("settings", COMMANDS)
        self.assertIn("logs", COMMANDS)
        self.assertIn("history", COMMANDS)
        self.assertIn("clear", COMMANDS)
        self.assertIn("quit", COMMANDS)
        self.assertIn("version", COMMANDS)
        self.assertIn("pwd", COMMANDS)

    def test_get_command(self):
        self.assertIsNotNone(get_command("help"))
        self.assertIsNone(get_command("nonexistent"))

    def test_command_result_defaults(self):
        r = CommandResult()
        self.assertTrue(r.continue_session)
        self.assertFalse(r.clear_screen)


if __name__ == "__main__":
    unittest.main()
