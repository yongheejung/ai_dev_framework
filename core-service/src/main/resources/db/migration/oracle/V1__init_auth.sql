CREATE TABLE app_user (
    id       VARCHAR2(36)  NOT NULL PRIMARY KEY,
    username VARCHAR2(100) NOT NULL UNIQUE,
    password VARCHAR2(255) NOT NULL
);

CREATE TABLE user_roles (
    user_id VARCHAR2(36) NOT NULL REFERENCES app_user (id),
    role    VARCHAR2(50) NOT NULL,
    PRIMARY KEY (user_id, role)
);
