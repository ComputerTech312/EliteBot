# sasl.py
import base64

NULL_BYTE = '\x00'
ENCODING = 'UTF-8'


async def handle_sasl(config, ircsend):
    """
    Handles SASL authentication by sending an AUTHENTICATE command.

    Parameters:
    config (dict): Configuration dictionary
    ircsend (function): Function to send IRC commands
    """
    await ircsend('AUTHENTICATE PLAIN')


async def handle_authenticate(args, config, ircsend):
    """
    Handles the AUTHENTICATE command response.

    Parameters:
    args (list): List of arguments from the AUTHENTICATE command
    config (dict): Configuration dictionary
    ircsend (function): Function to send IRC commands
    """
    if args[0] == '+':
        if 'SASLNick' in config['SASL'] and 'SASLPassword' in config['SASL']:
            authpass = (f'{config["SASL"]["SASLNick"]}{NULL_BYTE}'
                        f'{config["SASL"]["SASLNick"]}{NULL_BYTE}'
                        f'{config["SASL"]["SASLPassword"]}')
            ap_encoded = base64.b64encode(authpass.encode(ENCODING)).decode(ENCODING)
            await ircsend(f'AUTHENTICATE {ap_encoded}')
        else:
            raise KeyError('SASLNICK and/or SASLPASS not found in config')


async def handle_903(ircsend):
    """
    Handles the 903 command by sending a CAP END command.

    Parameters:
    ircsend (function): Function to send IRC commands
    """
    await ircsend('CAP END')
