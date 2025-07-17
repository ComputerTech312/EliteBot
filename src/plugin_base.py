class PluginBase:
    def __init__(self, bot_instance):
        """
        Constructor for the base plugin.

        :param bot_instance: Reference to the main bot instance
        """
        self.bot = bot_instance
        self.commands = {}

    async def handle_message(self, source_nick, channel, message):
        """
        Called when a message is received.

        :param source_nick: Nickname of the user who sent the message
        :param channel: Channel where the message was sent
        :param message: Content of the message
        """
        pass

    async def handle_command(self, source_nick, channel, cmd, cmd_args):
        """
        Called when a command is received.

        :param source_nick: Nickname of the user who sent the command
        :param channel: Channel where the command was sent
        :param cmd: The command name
        :param cmd_args: List of command arguments
        :return: True if command was handled, False otherwise
        """
        return False

    def on_connect(self):
        """
        Called when the bot connects to the server.
        """
        pass

    def on_disconnect(self):
        """
        Called when the bot disconnects from the server.
        """
        pass
