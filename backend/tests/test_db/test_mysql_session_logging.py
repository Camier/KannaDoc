"""Test for Fix #2: SQLAlchemy echo mode based on debug_mode"""
import pytest
from unittest.mock import patch
from app.db.mysql_session import MySQL

DB_URL = "test_db_url"


@pytest.mark.asyncio
async def test_sqlalchemy_echo_disabled_in_production():
    """
    CRITICAL FIX #2 VALIDATION
    
    Verify that SQLAlchemy echo mode is set to settings.debug_mode
    instead of hardcoded True.
    
    In production (DEBUG_MODE=false), this prevents SQL queries
    from being logged to stdout (security & performance fix).
    """
    with patch('app.db.mysql_session.settings') as mock_settings:
        # Simulate production configuration
        mock_settings.db_url = DB_URL
        mock_settings.db_pool_size = 10
        mock_settings.db_max_overflow = 20
        mock_settings.debug_mode = False
        
        with patch('app.db.mysql_session.create_async_engine') as mock_engine:
            mysql = MySQL()
            
            mock_engine.assert_called_once()
            call_args = mock_engine.call_args
            echo_value = call_args.kwargs.get('echo')
            
            assert echo_value == False


@pytest.mark.asyncio
async def test_sqlalchemy_echo_enabled_in_debug():
    """
    Verify that SQLAlchemy echo mode IS enabled when DEBUG_MODE=true.
    """
    with patch('app.db.mysql_session.settings') as mock_settings:
        # Simulate debug configuration
        mock_settings.db_url = DB_URL
        mock_settings.db_pool_size = 10
        mock_settings.db_max_overflow = 20
        mock_settings.debug_mode = True
        
        with patch('app.db.mysql_session.create_async_engine') as mock_engine:
            mysql = MySQL()
            
            mock_engine.assert_called_once()
            call_args = mock_engine.call_args
            echo_value = call_args.kwargs.get('echo')
            
            assert echo_value == True


@pytest.mark.asyncio
async def test_sqlalchemy_engine_parameters():
    """
    Verify that all engine creation parameters are correct.
    """
    with patch('app.db.mysql_session.settings') as mock_settings:
        mock_settings.db_url = DB_URL
        mock_settings.db_pool_size = 15
        mock_settings.db_max_overflow = 25
        mock_settings.debug_mode = False
        
        with patch('app.db.mysql_session.create_async_engine') as mock_engine:
            mysql = MySQL()
            
            call_args = mock_engine.call_args
            
            assert call_args.args[0] == DB_URL
            assert call_args.kwargs['echo'] == False
            assert call_args.kwargs['pool_size'] == 15
            assert call_args.kwargs['max_overflow'] == 25
            assert call_args.kwargs['pool_pre_ping'] == True
