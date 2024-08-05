INSERT_USER = """
    INSERT INTO users.googleid (uid, email, name, given_name, family_name, picture)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (uid) DO UPDATE SET
        email = EXCLUDED.email,
        name = EXCLUDED.name,
        given_name = EXCLUDED.given_name,
        family_name = EXCLUDED.family_name,
        picture = EXCLUDED.picture;
    """

FETCH_USER = """
    SELECT
        tu.email,
        tu.name,
        tu.given_name,
        tu.family_name,
        tu.picture
    FROM
        users.googleid as tu
    WHERE
        tu.uid = %s
    LIMIT 1;
    """

INSERT_SESSION = """
    INSERT INTO users.sessions (sid, uid, timestamp, credentials)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (sid) DO UPDATE
    SET timestamp = EXCLUDED.timestamp,
        credentials = EXCLUDED.credentials;
    """

FETCH_SESSION = """
    SELECT
        ts.uid,
        ts.timestamp,
        tu.email,
        tu.name,
        tu.given_name,
        tu.family_name,
        tu.picture,
        ts.credentials
    FROM
        users.sessions as ts
        JOIN users.googleid as tu ON ts.uid = tu.uid
    WHERE
        ts.sid = %s
    ORDER BY
        ts.timestamp DESC
    LIMIT 1;
    """

FETCH_USER_THREADS = """
    SELECT threads.tid
    FROM
        chats.threads as threads
        JOIN users.sessions as sessions ON threads.sid = sessions.sid
    WHERE
        sessions.uid = %s
    ORDER BY
        threads.last_used DESC;
    """

FETCH_THREAD_ID = """
    SELECT
        threads.sid,
        threads.tid,
        threads.summary,
        threads.last_used,
        sessions.uid
    FROM
        chats.threads as threads
        JOIN users.sessions as sessions ON threads.sid = sessions.sid
    WHERE true
        AND threads.tid = %s
        AND sessions.uid = %s
    LIMIT 1;
    """

FETCH_THREAD_MESSAGES = """
    SELECT msg.mid
    FROM
        chats.messages as msg
    WHERE
        msg.tid = %s
    ORDER BY
        msg.id DESC;
    """

PUT_THREAD_SAVE = """
    INSERT INTO chats.threads (sid, tid, summary, last_used)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (tid) DO UPDATE
    SET last_used = EXCLUDED.last_used,
        summary = EXCLUDED.summary;
    """

FETCH_MESSAGE = """
    SELECT
        msg.role,
        msg.content,
        msg.timestamp,
    FROM
        chats.messages as msg
    WHERE
        msg.mid = %s
    LIMIT 1;
    """

INSERT_MESSAGE = """
    INSERT INTO chats.messages (sid, tid, mid, role, content, timestamp)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (mid) DO UPDATE
    SET role = EXCLUDED.role,
        content = EXCLUDED.content;
    """
