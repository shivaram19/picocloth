# LinkedIn Profile Scraper

A Selenium-based Python tool to extract profile information from LinkedIn. This scraper automates the process of gathering key profile data including name, about section, work experience, and open-to-work status.

## ⚠️ Disclaimer

This tool is for educational purposes only. Web scraping LinkedIn may violate their Terms of Service. Use responsibly and at your own risk. LinkedIn actively blocks automated access, so this scraper may require manual intervention during login or verification steps.

## 🚀 Features

- ✅ Automated LinkedIn login using environment variables
- ✅ Support for both profile ID and full URL input
- ✅ Extracts comprehensive profile data:
  - Full name
  - About section
  - Previous company (most recent past employer)
  - Total number of companies worked for
  - Open to work status
- ✅ Graceful handling of missing sections
- ✅ Smart scrolling to load dynamic content
- ✅ JSON output (console + file)
- ✅ CLI with customizable options
- ✅ Detailed logging for debugging

## 📋 Prerequisites

- Python 3.7 or higher
- Google Chrome browser installed
- Active LinkedIn account

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd assesment
```

### 2. Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup environment variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your LinkedIn credentials:

```
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_secure_password
```

**⚠️ Security Note:** Never commit your `.env` file to version control!

## 📖 Usage

### Basic Usage

```bash
# Using profile ID only
python scraper.py --profile johndoe

# Using full profile URL
python scraper.py --profile https://www.linkedin.com/in/johndoe/
```

### With Headless Mode (not recommended for LinkedIn)

```bash
python scraper.py --profile johndoe --headless
```

**Note:** Headless mode may trigger LinkedIn's bot detection. It's recommended to run without headless mode for better success rates.

### Command Line Arguments

- `--profile` (required): LinkedIn profile ID or full URL
  - Example: `johndoe` or `https://www.linkedin.com/in/johndoe/`
- `--headless` (optional): Run browser in headless mode

## 📊 Output

The scraper outputs data in two ways:

### 1. Console Output

```json
{
  "profile_url": "https://www.linkedin.com/in/johndoe/",
  "name": "John Doe",
  "about": "Experienced software engineer...",
  "open_to_work": true,
  "previous_company": "Tech Corp",
  "total_companies_worked": 5,
  "companies_list": [
    "Current Company Inc",
    "Tech Corp",
    "StartupXYZ",
    "Digital Solutions Ltd",
    "Innovation Labs"
  ]
}
```

### 2. File Output

Results are automatically saved to `output.json` in the project directory.

## 🧪 Testing

### Quick Test

1. Set up your `.env` file with valid credentials
2. Run with a known LinkedIn profile:

```bash
python scraper.py --profile williamhgates
```

3. Check the console output and `output.json` file

### Troubleshooting Common Issues

#### Issue: Login fails or requires verification

**Solution:** 
- Run without `--headless` mode
- Manually complete verification steps in the browser window
- LinkedIn may send a verification email or require 2FA

#### Issue: "Element not found" errors

**Solution:**
- LinkedIn frequently changes their HTML structure
- Increase wait times in `utils.py`
- Run in non-headless mode to see what's happening
- Check if you're rate-limited or blocked

#### Issue: Captcha or security check

**Solution:**
- LinkedIn detects automation attempts
- Try running at different times
- Reduce scraping frequency
- Complete security checks manually when prompted

## 🏗️ Project Structure

```
assesment/
├── scraper.py          # Main scraper script
├── utils.py            # Helper functions (scroll, extract, etc.)
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── .env                # Your credentials (not in git)
├── .gitignore          # Git ignore rules
├── output.json         # Output file (generated)
└── README.md           # This file
```

## 📦 Dependencies

- **selenium** (4.16.0): Browser automation
- **webdriver-manager** (4.0.1): Automatic ChromeDriver management
- **python-dotenv** (1.0.0): Environment variable management

## 🔧 Advanced Configuration

### Modify Wait Times

Edit `scraper.py` to adjust timeouts:

```python
# Line ~32
self.wait = WebDriverWait(self.driver, 15)  # Change 15 to desired seconds
```

### Customize Scrolling

Edit `utils.py`:

```python
# Line ~66
scroll_to_load_content(driver, logger, scrolls=5, delay=1.5)
```

Increase `scrolls` or `delay` for profiles with extensive experience sections.

## 🚨 Limitations & Best Practices

### Limitations

1. **LinkedIn's Anti-Bot Measures**: LinkedIn actively blocks automated scraping
2. **Dynamic Selectors**: LinkedIn's HTML structure changes frequently
3. **Rate Limiting**: Too many requests may result in account restrictions
4. **Authentication**: May require manual verification steps
5. **Private Profiles**: Cannot access data from private/restricted profiles

### Best Practices

1. **Respect LinkedIn's ToS**: Use for educational purposes only
2. **Add Delays**: Don't scrape too frequently
3. **Use Real User Agents**: Already configured in the scraper
4. **Monitor for Changes**: LinkedIn updates their site regularly
5. **Handle Errors Gracefully**: The scraper includes error handling
6. **Avoid Headless Mode**: Less likely to be detected

## 🤝 Contributing

Feel free to submit issues or pull requests for improvements.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚙️ Git Setup & GitHub Push

### Initialize and Commit

```bash
# Add all files
git add .

# Commit
git commit -m "Initial commit: LinkedIn profile scraper"
```

### Push to GitHub

```bash
# Create a new repository on GitHub first, then:
git remote add origin https://github.com/yourusername/linkedin-scraper.git
git branch -M main
git push -u origin main
```

## 📞 Support

If you encounter issues:

1. Check the logs in the console
2. Verify your credentials in `.env`
3. Ensure Chrome browser is installed
4. Try running in non-headless mode
5. Check if LinkedIn is blocking your account

## 🎯 Example Use Cases

1. **Research**: Gather data for market research
2. **Recruitment**: Track candidate profiles (with permission)
3. **Learning**: Study web scraping techniques
4. **Automation**: Automate repetitive profile checks

---

**Remember:** Always respect website terms of service and user privacy. This tool is for educational purposes.