# Lachesis Discord Bot

Lachesis is a dynamic Discord bot that serves as a Game Master (GM) for role-playing adventures. Mostly planned with long-short term memory of conversation and its own internal train of thought asynchronous of user.

## Features

- **Character Creation**: Interactive character creation with dynamic questioning
- **Adventure System**: Run adventures with narrative storytelling and decision points
- **Memory System**: Short-term and long-term memory of conversations and events
- **State Management**: Track user state across different contexts
- **Extensibility**: Easily add new features through the modular design

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- Local Language Model (using LM Studio or similar)

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/lachesis-bot.git
   cd lachesis-bot
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration:
   ```
   DISCORD_BOT_TOKEN=your_discord_token
   LM_API_BASE=http://localhost:1234/v1
   MODEL_NAME=YourModelNameHere
   TEMPERATURE=0.8
   TOP_P=0.95
   ```

4. Start the bot:
   ```
   python main.py
   ```

## Usage

Once the bot is running, invite it to your Discord server and use the following commands:

- `!status` - Check your character's status
- `!profile` - Display your character profile
- `!adventure` - Start a new adventure
- `!character` - Begin character creation

You can also interact with Lachesis through natural conversation. She will guide you through character creation, adventures, and more.

## Project Structure

The project follows a modular design for easy extension and modification:

```
lachesis_bot/
├── main.py                    # Main entry point
├── .env                       # Environment variables
├── README.md                  # Documentation
├── requirements.txt           # Dependencies
├── data/                      # Data storage directory
│   ├── users/                 # User-specific data
│   ├── adventures/            # Adventure templates and data
│   └── system/                # System configuration
├── src/                       # Source code
│   ├── bot/                   # Bot core
│   ├── llm/                   # LLM integration
│   ├── managers/              # Data managers
│   ├── utils/                 # Utility functions
│   └── models/                # Data models
└── tests/                     # Tests
```

## Extending Lachesis

### Adding New Commands

To add a new command:

1. Define your command function in `src/bot/commands.py`
2. Register it in the function dispatcher in `main.py`
3. Update the prompt to include your new function

### Creating Adventure Templates

To create a new adventure template:

1. Create a JSON file in `data/adventures/templates/`
2. Follow the existing template format with scenes and options
3. The adventure will automatically be available for users

### Custom Character Attributes

To add custom character attributes:

1. Extend the `CharacterSheet` class in `src/models/profile.py`
2. Update the profile manager to handle your new attributes
3. Modify related commands as needed

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Discord.py for the Discord API integration
- OpenAI API for the language model interface

---
