# Contributing to OpenStreamBot

Thank you for considering contributing to OpenStreamBot! 🎉

## How to Contribute

### Reporting Bugs
- Use the [GitHub Issues](https://github.com/JanVanPommes/OpenStreamBot/issues) tracker
- Include your OS, Python version, and steps to reproduce
- Attach relevant logs if possible

### Suggesting Features
- Open an issue with the `enhancement` label
- Describe the use case and expected behavior
- Discuss before implementing major changes

### Pull Requests
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/AmazingFeature`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages: `git commit -m 'Add: Amazing new feature'`
6. Push to your fork: `git push origin feature/AmazingFeature`
7. Open a Pull Request

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and small

### Testing
- Test your changes locally before submitting
- Ensure the bot starts without errors
- Test both GUI launcher and headless mode

## Development Setup

```bash
# Clone your fork
git clone https://github.com/JanVanPommes/OpenStreamBot.git
cd OpenStreamBot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create config
cp config.example.yaml config.yaml
# Edit config.yaml with your credentials

# Run launcher
python launcher.py
```

## Questions?

Feel free to open an issue for any questions or join discussions!

---

**Thank you for making OpenStreamBot better!** ❤️
