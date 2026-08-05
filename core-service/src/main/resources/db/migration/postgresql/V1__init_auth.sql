CREATE TABLE app_user (
    id       VARCHAR(36)  NOT NULL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE user_roles (
    user_id VARCHAR(36) NOT NULL REFERENCES app_user (id),
    role    VARCHAR(50) NOT NULL,
    PRIMARY KEY (user_id, role)
);
