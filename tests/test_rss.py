import os
from unittest.mock import patch
from scripts.main import main

def test_rss_url_config_via_env():
    """
    Checks if the pipeline uses the RSS_FEED_URL environment variable.
    We mock fetch_recent_articles to avoid network calls and just check what URL it received.
    """
    mock_url = "https://example.com/custom-feed/"
    
    with patch("scripts.main.fetch_recent_articles") as mock_fetch:
        with patch.dict(os.environ, {"RSS_FEED_URL": mock_url, "GEMINI_API_KEY": "fake-key"}):
            with patch("scripts.main.generate_briefing"), \
                 patch("scripts.main.generate_audio"), \
                 patch("scripts.main.write_data_json"), \
                 patch("scripts.main.load_dotenv"), \
                 patch("sys.argv", ["scripts/main.py"]):
                
                try:
                    main()
                except SystemExit:
                    pass
                
                mock_fetch.assert_called_with(mock_url)

def test_rss_url_default():
    """
    Checks if the default RSS URL is used when no env var is set.
    """
    default_url = "https://techcrunch.com/category/artificial-intelligence/feed/"
    
    with patch("scripts.main.fetch_recent_articles") as mock_fetch:
        with patch.dict(os.environ, {}, clear=True):
             with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
                with patch("scripts.main.generate_briefing"), \
                     patch("scripts.main.generate_audio"), \
                     patch("scripts.main.write_data_json"), \
                     patch("scripts.main.load_dotenv"), \
                     patch("sys.argv", ["scripts/main.py"]):
                    
                    try:
                        main()
                    except SystemExit:
                        pass
                    
                    mock_fetch.assert_called_with(default_url)

