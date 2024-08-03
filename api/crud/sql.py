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
        credentials = EXCLUDED.credentials
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
