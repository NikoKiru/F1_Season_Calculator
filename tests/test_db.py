"""Tests for the database connection pooling functionality."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from db import (
    get_db,
    close_db,
    dispose_engine,
    dispose_all_engines,
    _get_engine,
    _engines,
    PooledConnection,
    init_db,
)


class TestConnectionPooling:
    """Tests for SQLAlchemy connection pooling."""

    def test_get_engine_creates_engine(self, app):
        """Test that _get_engine creates an engine for the database path."""
        with app.app_context():
            db_path = app.config['DATABASE']
            engine = _get_engine(db_path)
            assert engine is not None
            assert db_path in _engines

    def test_get_engine_reuses_engine(self, app):
        """Test that _get_engine returns the same engine for the same path."""
        with app.app_context():
            db_path = app.config['DATABASE']
            engine1 = _get_engine(db_path)
            engine2 = _get_engine(db_path)
            assert engine1 is engine2

    def test_get_db_returns_pooled_connection(self, app):
        """Test that get_db returns a PooledConnection."""
        with app.app_context():
            db = get_db()
            assert isinstance(db, PooledConnection)

    def test_get_db_reuses_connection_in_request(self, app):
        """Test that get_db returns the same connection within a request."""
        with app.app_context():
            db1 = get_db()
            db2 = get_db()
            assert db1 is db2

    def test_dispose_engine(self, app):
        """Test that dispose_engine removes the engine from cache."""
        with app.app_context():
            db_path = app.config['DATABASE']
            _get_engine(db_path)
            assert db_path in _engines
            dispose_engine(db_path)
            assert db_path not in _engines

    def test_dispose_engine_nonexistent(self, app):
        """Test that dispose_engine handles nonexistent path gracefully."""
        with app.app_context():
            # Should not raise an error
            dispose_engine("/nonexistent/path.db")


class TestPooledConnection:
    """Tests for the PooledConnection wrapper class."""

    def test_execute(self, app):
        """Test that execute works correctly."""
        with app.app_context():
            db = get_db()
            cursor = db.execute("SELECT COUNT(*) FROM championship_results")
            result = cursor.fetchone()
            assert result[0] >= 0

    def test_execute_with_params(self, app):
        """Test that execute works with parameters."""
        with app.app_context():
            db = get_db()
            cursor = db.execute(
                "SELECT * FROM championship_results WHERE winner = ?",
                ("VER",)
            )
            results = cursor.fetchall()
            assert isinstance(results, list)

    def test_executemany(self, app):
        """Test that executemany works correctly."""
        with app.app_context():
            db = get_db()
            # Create a temp table for testing
            db.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER, name TEXT)")
            db.executemany(
                "INSERT INTO test_table (id, name) VALUES (?, ?)",
                [(1, "test1"), (2, "test2")]
            )
            db.commit()
            cursor = db.execute("SELECT COUNT(*) FROM test_table")
            assert cursor.fetchone()[0] == 2
            db.execute("DROP TABLE test_table")
            db.commit()

    def test_commit(self, app):
        """Test that commit works correctly."""
        with app.app_context():
            db = get_db()
            # Should not raise an error
            db.commit()

    def test_rollback(self, app):
        """Test that rollback works correctly."""
        with app.app_context():
            db = get_db()
            # Create a temp table
            db.execute("CREATE TABLE IF NOT EXISTS test_rollback (id INTEGER)")
            db.commit()
            # Insert and rollback
            db.execute("INSERT INTO test_rollback (id) VALUES (1)")
            db.rollback()
            cursor = db.execute("SELECT COUNT(*) FROM test_rollback")
            assert cursor.fetchone()[0] == 0
            db.execute("DROP TABLE test_rollback")
            db.commit()

    def test_row_factory(self, app):
        """Test that row factory allows column access by name."""
        with app.app_context():
            db = get_db()
            cursor = db.execute(
                "SELECT winner, num_races FROM championship_results LIMIT 1"
            )
            row = cursor.fetchone()
            assert row is not None
            # Should be able to access by column name
            assert 'winner' in row.keys()
            assert 'num_races' in row.keys()


class TestCloseDb:
    """Tests for close_db function."""

    def test_close_db_with_connection(self, app):
        """Test that close_db closes an existing connection."""
        with app.app_context():
            # Get a connection
            get_db()
            # Close should not raise
            close_db()

    def test_close_db_without_connection(self, app):
        """Test that close_db handles no connection gracefully."""
        with app.app_context():
            # Don't get a connection first
            # Close should not raise
            close_db()


class TestEngineConfiguration:
    """Tests for engine configuration."""

    def test_engine_pool_settings(self, app):
        """Test that engine has correct pool settings."""
        with app.app_context():
            db_path = app.config['DATABASE']
            engine = _get_engine(db_path)
            pool = engine.pool
            assert pool.size() == 5  # pool_size
            assert pool._max_overflow == 10  # max_overflow

    def test_pragmas_applied(self, app):
        """Test that SQLite pragmas are applied."""
        with app.app_context():
            db = get_db()
            cursor = db.execute("PRAGMA journal_mode")
            result = cursor.fetchone()[0]
            assert result.lower() == "wal"

            cursor = db.execute("PRAGMA synchronous")
            result = cursor.fetchone()[0]
            assert result == 1  # NORMAL = 1


class TestDisposeAllEngines:
    """Tests for dispose_all_engines function."""

    def test_dispose_all_engines(self, app):
        """Test that dispose_all_engines clears all engines."""
        with app.app_context():
            # Create an engine
            db_path = app.config['DATABASE']
            _get_engine(db_path)
            assert len(_engines) > 0
            # Dispose all
            dispose_all_engines()
            assert len(_engines) == 0

    def test_dispose_all_engines_empty(self, app):
        """Test that dispose_all_engines handles empty cache."""
        # Clear first
        dispose_all_engines()
        # Should not raise
        dispose_all_engines()
        assert len(_engines) == 0


class TestInitDb:
    """Tests for init_db function."""

    def test_init_db_creates_tables(self):
        """Test that init_db creates the required tables."""
        # Create a temporary database
        db_fd, db_path = tempfile.mkstemp()
        try:
            flask_app.config['DATABASE'] = db_path

            with flask_app.app_context():
                # Dispose any existing engines
                dispose_all_engines()
                close_db()

                # Initialize the database
                init_db(clear_existing=False)

                # Verify tables exist
                db = get_db()
                cursor = db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = [row[0] for row in cursor.fetchall()]
                assert 'championship_results' in tables
                assert 'driver_statistics' in tables
                assert 'position_results' in tables

        finally:
            dispose_all_engines()
            os.close(db_fd)
            try:
                os.unlink(db_path)
                for ext in ["-wal", "-shm"]:
                    if os.path.exists(db_path + ext):
                        os.unlink(db_path + ext)
            except PermissionError:
                pass

    def test_init_db_with_clear_existing(self):
        """Test that init_db with clear_existing attempts to clear old data.

        Note: On Windows, file locks may prevent deletion, but init_db
        should handle this gracefully with a warning.
        """
        db_fd, db_path = tempfile.mkstemp()
        try:
            flask_app.config['DATABASE'] = db_path

            with flask_app.app_context():
                dispose_all_engines()
                close_db()

                # Initialize and add some data
                init_db(clear_existing=False)
                db = get_db()
                db.execute(
                    "INSERT INTO championship_results "
                    "(num_races, rounds, standings, winner, points) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (3, '1,2,3', 'VER,NOR,LEC', 'VER', '68,61,48')
                )
                db.commit()
                cursor = db.execute("SELECT COUNT(*) FROM championship_results")
                initial_count = cursor.fetchone()[0]
                assert initial_count == 1

                close_db()
                dispose_all_engines()

            # Re-enter context for clear operation
            with flask_app.app_context():
                # Now clear and reinitialize - may warn on Windows but should work
                init_db(clear_existing=True)

                # Verify the operation completed (table exists, possibly empty)
                db = get_db()
                cursor = db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='championship_results'"
                )
                assert cursor.fetchone() is not None

        finally:
            dispose_all_engines()
            os.close(db_fd)
            try:
                os.unlink(db_path)
                for ext in ["-wal", "-shm"]:
                    if os.path.exists(db_path + ext):
                        os.unlink(db_path + ext)
            except PermissionError:
                pass

    def test_init_db_creates_indexes(self):
        """Test that init_db creates the required indexes."""
        db_fd, db_path = tempfile.mkstemp()
        try:
            flask_app.config['DATABASE'] = db_path

            with flask_app.app_context():
                dispose_all_engines()
                close_db()
                init_db(clear_existing=False)

                db = get_db()
                cursor = db.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
                indexes = [row[0] for row in cursor.fetchall()]
                assert 'idx_winner' in indexes
                assert 'idx_num_races' in indexes
                assert 'idx_driver_position' in indexes

        finally:
            dispose_all_engines()
            os.close(db_fd)
            try:
                os.unlink(db_path)
                for ext in ["-wal", "-shm"]:
                    if os.path.exists(db_path + ext):
                        os.unlink(db_path + ext)
            except PermissionError:
                pass

    def test_init_db_creates_win_probability_cache_table(self):
        """Test that init_db creates the win_probability_cache table."""
        db_fd, db_path = tempfile.mkstemp()
        try:
            flask_app.config['DATABASE'] = db_path

            with flask_app.app_context():
                dispose_all_engines()
                close_db()
                init_db(clear_existing=False)

                db = get_db()
                cursor = db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='win_probability_cache'"
                )
                assert cursor.fetchone() is not None

                # Verify table structure
                cursor = db.execute("PRAGMA table_info(win_probability_cache)")
                columns = {row[1]: row[2] for row in cursor.fetchall()}
                assert 'driver_code' in columns
                assert 'num_races' in columns
                assert 'win_count' in columns
                assert 'total_at_length' in columns

        finally:
            dispose_all_engines()
            os.close(db_fd)
            try:
                os.unlink(db_path)
                for ext in ["-wal", "-shm"]:
                    if os.path.exists(db_path + ext):
                        os.unlink(db_path + ext)
            except PermissionError:
                pass

    def test_init_db_creates_win_probability_indexes(self):
        """Test that init_db creates indexes for win_probability_cache."""
        db_fd, db_path = tempfile.mkstemp()
        try:
            flask_app.config['DATABASE'] = db_path

            with flask_app.app_context():
                dispose_all_engines()
                close_db()
                init_db(clear_existing=False)

                db = get_db()
                cursor = db.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
                indexes = [row[0] for row in cursor.fetchall()]
                assert 'idx_prob_driver' in indexes
                assert 'idx_prob_num_races' in indexes

        finally:
            dispose_all_engines()
            os.close(db_fd)
            try:
                os.unlink(db_path)
                for ext in ["-wal", "-shm"]:
                    if os.path.exists(db_path + ext):
                        os.unlink(db_path + ext)
            except PermissionError:
                pass


class TestWinProbabilityCache:
    """Tests for win_probability_cache functionality."""

    def test_win_probability_cache_data(self, app):
        """Test that win_probability_cache contains expected data."""
        with app.app_context():
            db = get_db()
            cursor = db.execute(
                "SELECT * FROM win_probability_cache WHERE driver_code = 'VER' ORDER BY num_races"
            )
            rows = cursor.fetchall()
            assert len(rows) == 4  # 4 different season lengths in test data
            # Check VER's wins at different season lengths
            ver_data = {row['num_races']: row['win_count'] for row in rows}
            assert ver_data[3] == 1  # 1 win at 3 races
            assert ver_data[4] == 1  # 1 win at 4 races
            assert ver_data[5] == 0  # 0 wins at 5 races
            assert ver_data[6] == 1  # 1 win at 6 races

    def test_win_probability_cache_totals(self, app):
        """Test that total_at_length values are correct."""
        with app.app_context():
            db = get_db()
            cursor = db.execute(
                "SELECT DISTINCT num_races, total_at_length FROM win_probability_cache ORDER BY num_races"
            )
            rows = cursor.fetchall()
            totals = {row['num_races']: row['total_at_length'] for row in rows}
            assert totals[3] == 2  # 2 championships at 3 races
            assert totals[4] == 1  # 1 championship at 4 races
            assert totals[5] == 1  # 1 championship at 5 races
            assert totals[6] == 1  # 1 championship at 6 races

    def test_win_probability_cache_all_drivers(self, app):
        """Test that all drivers have cache entries."""
        with app.app_context():
            db = get_db()
            cursor = db.execute(
                "SELECT DISTINCT driver_code FROM win_probability_cache ORDER BY driver_code"
            )
            drivers = [row['driver_code'] for row in cursor.fetchall()]
            assert 'VER' in drivers
            assert 'NOR' in drivers
            assert 'LEC' in drivers
            assert 'HAM' in drivers
            assert 'RUS' in drivers
            assert 'PIA' in drivers
