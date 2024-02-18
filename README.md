# IRC Bot

This is an IRC bot written in Python. It connects to an IRC server, authenticates using SASL if desired, and responds to various commands. It is also able to join and save channels that it is invited to.

## Requirements

- Python 3
- A configuration file `config.json` containing the following variables:
  - `BSERVER`: the IRC server to connect to
  - `BPORT`: the port to use for the connection (can be preceded with a `+` to specify a secure connection)
  - `BNICK`: the desired bot nickname
  - `BIDENT`: the bot's ident
  - `BNAME`: the bot's real name
  - `UseSASL`: a boolean indicating whether or not to use SASL authentication
  - `SANICK`: the bot's SASL account name (if using SASL)
  - `SAPASS`: the bot's SASL password (if using SASL)
  
## Usage

To run the bot, simply execute the script with `python3 elitebot.py config.json`. The bot will connect to the specified server and authenticate if necessary. It will then listen for commands and respond accordingly.

## Commands

The following commands are recognized by the bot:

- `&moo`: makes the bot moo.
- `&join`: makes the bot join the specified channel.
- `&part`: makes the bot part the current channel if a channel is not specified.
- `&quit`: makes the bot quit.

## Saving Channels

The bot is able to save a list of channels that it should automatically join upon connecting to the server. 

## Contributing

If you have any suggestions or improvements for the bot, feel free to create a pull request.
