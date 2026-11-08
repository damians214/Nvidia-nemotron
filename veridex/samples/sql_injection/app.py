"""Intentionally vulnerable SQLite example for static investigation only."""
import sqlite3


def get_user(conn: sqlite3.Connection, username: str):
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    return conn.execute(query).fetchone()
