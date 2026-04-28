from unittest.mock import MagicMock, patch
import pytest

# We patch the globals in app before importing
with patch("google.cloud.bigquery.Client"), patch("google.cloud.language_v2.LanguageServiceClient"):
    from app import _log_event_to_bigquery, _is_safe_input, _archive_event_to_gcs
    import app

def test_archive_event_to_gcs_disabled():
    app._GCS_OK = False
    _archive_event_to_gcs("test", {})

def test_archive_event_to_gcs_enabled():
    app._GCS_OK = True
    app._gcs_bucket = MagicMock()
    _archive_event_to_gcs("test", {"foo": "bar"})
    app._gcs_bucket.blob.assert_called_once()
    app._gcs_bucket.blob().upload_from_string.assert_called_once()

def test_log_event_to_bigquery_disabled():
    app._BQ_OK = False
    _log_event_to_bigquery("test", {})

def test_log_event_to_bigquery_enabled():
    app._BQ_OK = True
    app._BQ_TABLE = "test_table"
    app._bq_client = MagicMock()
    app._bq_client.insert_rows_json.return_value = []
    _log_event_to_bigquery("test", {"foo": "bar"})
    app._bq_client.insert_rows_json.assert_called_once()

def test_is_safe_input_disabled():
    app._NL_OK = False
    assert _is_safe_input("This is a test message that is long enough") == True

def test_is_safe_input_enabled_safe():
    app._NL_OK = True
    app._nl_client = MagicMock()
    
    mock_category = MagicMock()
    mock_category.name = "Toxic"
    mock_category.confidence = 0.5 # Safe
    
    mock_result = MagicMock()
    mock_result.moderation_categories = [mock_category]
    app._nl_client.moderate_text.return_value = mock_result
    
    assert _is_safe_input("This is a test message that is long enough") == True

def test_is_safe_input_enabled_unsafe():
    app._NL_OK = True
    app._nl_client = MagicMock()
    
    mock_category = MagicMock()
    mock_category.name = "Toxic"
    mock_category.confidence = 0.9 # Unsafe
    
    mock_result = MagicMock()
    mock_result.moderation_categories = [mock_category]
    app._nl_client.moderate_text.return_value = mock_result
    
    assert _is_safe_input("This is a test message that is long enough") == False
