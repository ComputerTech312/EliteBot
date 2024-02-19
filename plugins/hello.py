from src.plugin_base import PluginBase

class WhoisPlugin(PluginBase):
    def __init__(self, bot):
        super().__init__(bot)
        self.pending_whois = {}

    def handle_message(self, source_nick, channel, message):
        message_parts = message.split()
        if message_parts[0] == '@whois':
            self.bot.ircsend(f'WHOIS {source_nick}')
            self.pending_whois[source_nick] = channel
            print(f"Sent WHOIS for {source_nick}")
        elif ' | ' in message:
            parts = message.split(' | ')
            command = parts[2].split(': ')[1]
            if command == '311':
                args = parts[3].split(': ')[1].strip('[]').split(', ')
                nick = args[1].strip('\'')
                hostmask = args[3].strip('\'')
                if nick in self.pending_whois:
                    channel = self.pending_whois[nick]
                    self.bot.ircsend(f'PRIVMSG {channel} :pew')
                    print(f"Sent 'pew' to {channel}")
                    del self.pending_whois[nick]