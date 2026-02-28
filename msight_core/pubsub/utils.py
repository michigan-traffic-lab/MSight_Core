"""Pub/sub configuration utilities.

This module provides helper functions for generating configuration dictionaries
for various pub/sub backends (NATS and Kafka). These functions read environment
variables and construct properly formatted configuration objects that can be
passed to the corresponding PubSub backend constructors.

The configuration functions handle:
- Server/broker connection strings
- Authentication credentials (various mechanisms)
- TLS/SSL encryption settings
- Consumer/queue group identifiers

By centralizing configuration logic, these utilities ensure consistent
environment variable naming and provide validation and error messages
for misconfigured settings.

Example:
    Configure NATS with authentication::

        import os
        from msight_core.pubsub import NATSPubSub
        from msight_core.pubsub.utils import get_nats_config

        os.environ["MSIGHT_NATS_SERVERS"] = "['nats://server1:4222', 'nats://server2:4222']"
        os.environ["MSIGHT_NATS_USERNAME"] = "myuser"
        os.environ["MSIGHT_NATS_PASSWORD"] = "mypass"
        os.environ["MSIGHT_NATS_USE_TLS"] = "true"

        config = get_nats_config(group_id="my_workers")
        nats = NATSPubSub(config)

    Configure Kafka with SASL and TLS::

        import os
        from msight_core.pubsub import KafkaPubSub
        from msight_core.pubsub.utils import get_kafka_config

        os.environ["MSIGHT_KAFKA_SERVERS"] = "['broker1:9093', 'broker2:9093']"
        os.environ["MSIGHT_KAFKA_SASL_MECHANISM"] = "SCRAM-SHA-256"
        os.environ["MSIGHT_KAFKA_SASL_USERNAME"] = "admin"
        os.environ["MSIGHT_KAFKA_SASL_PASSWORD"] = "secret"
        os.environ["MSIGHT_KAFKA_USE_TLS"] = "true"
        os.environ["MSIGHT_KAFKA_TLS_CA_CERT_FILE"] = "/etc/kafka/ca.pem"

        config = get_kafka_config(group_id="processors")
        kafka = KafkaPubSub(config)

See Also:
    - :class:`msight_core.pubsub.NATSPubSub`: NATS backend implementation
    - :class:`msight_core.pubsub.KafkaPubSub`: Kafka backend implementation
    - :func:`msight_core.utils.get_redis_client`: Redis client configuration
"""

import os
import ast


def get_nats_config(group_id):
    """Get NATS configuration with support for TLS and authentication.
    
    Reads environment variables and constructs a configuration dictionary
    for connecting to NATS servers. Supports multiple authentication methods
    and TLS encryption options. The configuration can be passed directly
    to :class:`NATSPubSub` constructor.
    
    Supports:
    - Multiple server connections with automatic failover
    - Username/password authentication
    - Token-based authentication
    - NKey authentication (NATS 2.0+)
    - JWT authentication with user credentials
    - Credentials file authentication (.creds files)
    - TLS/SSL with optional client certificates
    
    Environment Variables:
        MSIGHT_NATS_SERVERS: List of NATS server URLs (default: "['nats://localhost:4222']")
            Format: String representation of Python list, e.g., "['nats://server1:4222', 'nats://server2:4222']"
        MSIGHT_NATS_USERNAME: Username for authentication (optional)
        MSIGHT_NATS_PASSWORD: Password for authentication (optional)
        MSIGHT_NATS_TOKEN: Token for authentication (optional, mutually exclusive with username/password)
        MSIGHT_NATS_NKEY_SEED: NKey seed for authentication (optional, NATS 2.0+)
        MSIGHT_NATS_USER_JWT: JWT token for user authentication (optional)
        MSIGHT_NATS_USER_CREDENTIALS: Path to .creds file containing JWT and NKey (optional)
        MSIGHT_NATS_USE_TLS: Enable TLS/SSL ("true"/"1"/"yes", default: "false")
        MSIGHT_NATS_TLS_CERT_FILE: Client certificate file path (optional)
        MSIGHT_NATS_TLS_KEY_FILE: Client key file path (optional)
        MSIGHT_NATS_TLS_CA_CERT_FILE: CA certificate file path (optional)
    
    Args:
        group_id (str or None): Consumer group identifier for JetStream subscriptions.
            When using queue groups, all subscribers with the same group_id will
            share message delivery (load balancing). Pass None for no queue group.
    
    Returns:
        nats_config (dict): NATS configuration dictionary with the following structure:
            - servers (list): List of server URLs
            - group_id (str, optional): Queue group name if provided
            - user (str, optional): Username for authentication
            - password (str, optional): Password for authentication
            - token (str, optional): Authentication token
            - nkeys_seed (str, optional): NKey seed
            - user_jwt (str, optional): JWT token
            - user_credentials (str, optional): Path to credentials file
            - tls (bool, optional): TLS enabled flag
            - tls_ca_cert (str, optional): CA certificate path
            - tls_cert (str, optional): Client certificate path
            - tls_key (str, optional): Client key path
    
    Raises:
        ValueError: If MSIGHT_NATS_SERVERS is not a valid Python list string.
    
    Example:
        Basic configuration with username/password::

            import os
            os.environ["MSIGHT_NATS_SERVERS"] = "['nats://localhost:4222']"
            os.environ["MSIGHT_NATS_USERNAME"] = "myuser"
            os.environ["MSIGHT_NATS_PASSWORD"] = "mypass"

            config = get_nats_config(group_id="workers")
            # Returns: {
            #     'servers': ['nats://localhost:4222'],
            #     'group_id': 'workers',
            #     'user': 'myuser',
            #     'password': 'mypass'
            # }

        With TLS and credentials file::

            import os
            os.environ["MSIGHT_NATS_SERVERS"] = "['nats://server:4222']"
            os.environ["MSIGHT_NATS_USER_CREDENTIALS"] = "/path/to/user.creds"
            os.environ["MSIGHT_NATS_USE_TLS"] = "true"
            os.environ["MSIGHT_NATS_TLS_CA_CERT_FILE"] = "/etc/nats/ca.pem"

            config = get_nats_config(group_id=None)

        Multiple servers with token auth::

            import os
            os.environ["MSIGHT_NATS_SERVERS"] = "['nats://s1:4222', 'nats://s2:4222', 'nats://s3:4222']"
            os.environ["MSIGHT_NATS_TOKEN"] = "my-secret-token"

            config = get_nats_config(group_id="my_group")
    
    Note:
        - Only one authentication method should be used at a time
        - Credentials file (.creds) contains both JWT and NKey, simplifying authentication
        - TLS verification is enabled by default for security
        - Multiple servers provide automatic failover and reconnection
    
    See Also:
        :class:`msight_core.pubsub.NATSPubSub`: NATS backend implementation
    """
    nats_servers = os.getenv("MSIGHT_NATS_SERVERS", "['nats://localhost:4222']")
    try:
        servers = ast.literal_eval(nats_servers)
        if not isinstance(servers, list):
            raise ValueError
    except Exception:
        raise ValueError("MSIGHT_NATS_SERVERS must be a string like \"['nats://ip1:4222', 'nats://ip2:4222']\"")
    
    config = {
        "servers": servers
    }
    
    if group_id is not None:
        config["group_id"] = group_id
    
    # Username/password authentication
    username = os.getenv("MSIGHT_NATS_USERNAME", None)
    password = os.getenv("MSIGHT_NATS_PASSWORD", None)
    if username:
        config["user"] = username
    if password:
        config["password"] = password
    
    # Token authentication
    token = os.getenv("MSIGHT_NATS_TOKEN", None)
    if token:
        config["token"] = token
    
    # NKey authentication
    nkey_seed = os.getenv("MSIGHT_NATS_NKEY_SEED", None)
    if nkey_seed:
        config["nkeys_seed"] = nkey_seed
    
    # JWT authentication
    user_jwt = os.getenv("MSIGHT_NATS_USER_JWT", None)
    if user_jwt:
        config["user_jwt"] = user_jwt
    
    # Credentials file (contains both JWT and NKey)
    user_credentials = os.getenv("MSIGHT_NATS_USER_CREDENTIALS", None)
    if user_credentials:
        config["user_credentials"] = user_credentials
    
    # TLS/SSL configuration
    use_tls = os.getenv("MSIGHT_NATS_USE_TLS", "false").lower() in ["true", "1", "yes"]
    if use_tls:
        import ssl
        tls_config = {
            "tls": True
        }
        
        # CA certificate
        tls_ca_cert = os.getenv("MSIGHT_NATS_TLS_CA_CERT_FILE", None)
        if tls_ca_cert:
            ssl_ctx = ssl.create_default_context(cafile=tls_ca_cert)
            tls_config["tls"] = ssl_ctx
        
        # Client certificate and key
        tls_cert = os.getenv("MSIGHT_NATS_TLS_CERT_FILE", None)
        tls_key = os.getenv("MSIGHT_NATS_TLS_KEY_FILE", None)
        if tls_cert:
            tls_config["tls_cert"] = tls_cert
        if tls_key:
            tls_config["tls_key"] = tls_key
        
        config.update(tls_config)
    
    return config

def get_kafka_config(group_id):
    """Get Kafka configuration with support for TLS and SASL authentication.
    
    Reads environment variables and constructs a configuration dictionary
    for connecting to Kafka brokers. Supports multiple SASL authentication
    mechanisms and TLS encryption. The configuration can be passed directly
    to :class:`KafkaPubSub` constructor.
    
    Automatically selects the appropriate security protocol based on the
    configured authentication and encryption settings:
    - PLAINTEXT: No TLS, no SASL (default)
    - SASL_PLAINTEXT: SASL authentication without TLS
    - SSL: TLS encryption without SASL
    - SASL_SSL: Both TLS encryption and SASL authentication
    
    Supports:
    - Multiple broker connections with automatic failover
    - SASL authentication mechanisms:
      - PLAIN (username/password, simplest but least secure)
      - SCRAM-SHA-256 (salted challenge response, recommended)
      - SCRAM-SHA-512 (strongest salted challenge response)
      - OAUTHBEARER (OAuth 2.0 bearer token authentication)
    - TLS/SSL with optional client certificates (mutual TLS)
    - Certificate verification and hostname checking
    
    Environment Variables:
        MSIGHT_KAFKA_SERVERS: List of Kafka broker addresses (default: "['localhost:9092']")
            Format: String representation of Python list, e.g., "['broker1:9092', 'broker2:9092']"
        MSIGHT_KAFKA_SASL_MECHANISM: SASL mechanism - PLAIN, SCRAM-SHA-256, SCRAM-SHA-512, OAUTHBEARER (optional)
        MSIGHT_KAFKA_SASL_USERNAME: Username for SASL authentication (required for PLAIN/SCRAM mechanisms)
        MSIGHT_KAFKA_SASL_PASSWORD: Password for SASL authentication (required for PLAIN/SCRAM mechanisms)
        MSIGHT_KAFKA_SASL_OAUTH_TOKEN: OAuth bearer token for OAUTHBEARER (required for OAUTHBEARER mechanism)
        MSIGHT_KAFKA_USE_TLS: Enable TLS/SSL ("true"/"1"/"yes", default: "false")
        MSIGHT_KAFKA_TLS_CERT_FILE: Client certificate file path (optional, for mutual TLS)
        MSIGHT_KAFKA_TLS_KEY_FILE: Client key file path (optional, for mutual TLS)
        MSIGHT_KAFKA_TLS_CA_CERT_FILE: CA certificate file path (optional, for server verification)
        MSIGHT_KAFKA_TLS_VERIFY: Verify server certificate ("true"/"1"/"yes", default: "true")
        MSIGHT_KAFKA_TLS_CHECK_HOSTNAME: Check hostname in certificate ("true"/"1"/"yes", default: "true")
    
    Args:
        group_id (str): Consumer group identifier. All consumers with the same
            group_id will share partition assignments and message consumption
            (load balancing). This is required for Kafka (unlike NATS where it's optional).
    
    Returns:
        kafka_config (dict): Kafka configuration dictionary with the following structure:
            - servers (list): List of broker addresses
            - group_id (str): Consumer group identifier
            - sasl_mechanism (str, optional): SASL mechanism name
            - sasl_plain_username (str, optional): SASL username
            - sasl_plain_password (str, optional): SASL password
            - sasl_oauth_token (str, optional): OAuth token
            - security_protocol (str, optional): Security protocol (PLAINTEXT/SASL_PLAINTEXT/SSL/SASL_SSL)
            - ssl_check_hostname (bool, optional): Hostname verification flag
            - ssl_verify (bool, optional): Certificate verification flag
            - ssl_cafile (str, optional): CA certificate path
            - ssl_certfile (str, optional): Client certificate path
            - ssl_keyfile (str, optional): Client key path
    
    Raises:
        ValueError: If:
            - MSIGHT_KAFKA_SERVERS is not a valid Python list string
            - SASL mechanism is not one of the supported types
            - Required authentication credentials are missing for the selected SASL mechanism
    
    Example:
        Basic configuration (no auth, no TLS)::

            import os
            os.environ["MSIGHT_KAFKA_SERVERS"] = "['localhost:9092']"

            config = get_kafka_config(group_id="my_consumers")
            # Returns: {
            #     'servers': ['localhost:9092'],
            #     'group_id': 'my_consumers'
            # }

        With SCRAM-SHA-256 and TLS (recommended for production)::

            import os
            os.environ["MSIGHT_KAFKA_SERVERS"] = "['broker1:9093', 'broker2:9093']"
            os.environ["MSIGHT_KAFKA_SASL_MECHANISM"] = "SCRAM-SHA-256"
            os.environ["MSIGHT_KAFKA_SASL_USERNAME"] = "admin"
            os.environ["MSIGHT_KAFKA_SASL_PASSWORD"] = "secret"
            os.environ["MSIGHT_KAFKA_USE_TLS"] = "true"
            os.environ["MSIGHT_KAFKA_TLS_CA_CERT_FILE"] = "/etc/kafka/ca-cert.pem"

            config = get_kafka_config(group_id="secure_processors")
            # security_protocol will be automatically set to "SASL_SSL"

        With mutual TLS (no SASL)::

            import os
            os.environ["MSIGHT_KAFKA_SERVERS"] = "['broker:9093']"
            os.environ["MSIGHT_KAFKA_USE_TLS"] = "true"
            os.environ["MSIGHT_KAFKA_TLS_CA_CERT_FILE"] = "/etc/kafka/ca.pem"
            os.environ["MSIGHT_KAFKA_TLS_CERT_FILE"] = "/etc/kafka/client.pem"
            os.environ["MSIGHT_KAFKA_TLS_KEY_FILE"] = "/etc/kafka/client-key.pem"

            config = get_kafka_config(group_id="mtls_consumers")
            # security_protocol will be automatically set to "SSL"

        With OAuth bearer token::

            import os
            os.environ["MSIGHT_KAFKA_SERVERS"] = "['broker:9092']"
            os.environ["MSIGHT_KAFKA_SASL_MECHANISM"] = "OAUTHBEARER"
            os.environ["MSIGHT_KAFKA_SASL_OAUTH_TOKEN"] = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

            config = get_kafka_config(group_id="oauth_group")
    
    Note:
        - Consumer group ID is mandatory for Kafka (used for partition assignment)
        - SCRAM-SHA-256 or SCRAM-SHA-512 are recommended over PLAIN for security
        - Always use TLS in production to encrypt data in transit
        - Mutual TLS (client certificates) provides additional authentication layer
        - security_protocol is automatically determined from TLS and SASL settings
    
    See Also:
        :class:`msight_core.pubsub.KafkaPubSub`: Kafka backend implementation
    """
    kafka_servers = os.getenv("MSIGHT_KAFKA_SERVERS", "['localhost:9092']")
    try:
        servers = ast.literal_eval(kafka_servers)
        if not isinstance(servers, list):
            raise ValueError
    except Exception:
        raise ValueError(f"MSIGHT_KAFKA_SERVERS must be a string like \"['ip1:9092', 'ip2:9092']\", got {kafka_servers}")

    config = {
        "servers": servers,
        "group_id": group_id
    }
    
    # SASL authentication
    sasl_mechanism = os.getenv("MSIGHT_KAFKA_SASL_MECHANISM", None)
    if sasl_mechanism:
        sasl_mechanism = sasl_mechanism.upper()
        if sasl_mechanism not in ["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"]:
            raise ValueError(
                f"MSIGHT_KAFKA_SASL_MECHANISM must be one of: PLAIN, SCRAM-SHA-256, "
                f"SCRAM-SHA-512, OAUTHBEARER. Got: {sasl_mechanism}"
            )
        
        config["sasl_mechanism"] = sasl_mechanism
        
        # Username/password for PLAIN and SCRAM mechanisms
        if sasl_mechanism in ["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"]:
            sasl_username = os.getenv("MSIGHT_KAFKA_SASL_USERNAME", None)
            sasl_password = os.getenv("MSIGHT_KAFKA_SASL_PASSWORD", None)
            
            if not sasl_username or not sasl_password:
                raise ValueError(
                    f"MSIGHT_KAFKA_SASL_USERNAME and MSIGHT_KAFKA_SASL_PASSWORD are required "
                    f"for {sasl_mechanism} authentication"
                )
            
            config["sasl_plain_username"] = sasl_username
            config["sasl_plain_password"] = sasl_password
        
        # OAuth token for OAUTHBEARER
        elif sasl_mechanism == "OAUTHBEARER":
            oauth_token = os.getenv("MSIGHT_KAFKA_SASL_OAUTH_TOKEN", None)
            if not oauth_token:
                raise ValueError(
                    "MSIGHT_KAFKA_SASL_OAUTH_TOKEN is required for OAUTHBEARER authentication"
                )
            config["sasl_oauth_token"] = oauth_token
    
    # TLS/SSL configuration
    use_tls = os.getenv("MSIGHT_KAFKA_USE_TLS", "false").lower() in ["true", "1", "yes"]
    if use_tls:
        config["security_protocol"] = "SSL"
        
        # If SASL is also enabled, use SASL_SSL protocol
        if sasl_mechanism:
            config["security_protocol"] = "SASL_SSL"
        
        # TLS verification (default: True)
        tls_verify = os.getenv("MSIGHT_KAFKA_TLS_VERIFY", "true").lower() in ["true", "1", "yes"]
        config["ssl_check_hostname"] = os.getenv("MSIGHT_KAFKA_TLS_CHECK_HOSTNAME", "true").lower() in ["true", "1", "yes"]
        
        if not tls_verify:
            config["ssl_verify"] = False
        
        # CA certificate
        tls_ca_cert = os.getenv("MSIGHT_KAFKA_TLS_CA_CERT_FILE", None)
        if tls_ca_cert:
            config["ssl_cafile"] = tls_ca_cert
        
        # Client certificate and key
        tls_cert = os.getenv("MSIGHT_KAFKA_TLS_CERT_FILE", None)
        tls_key = os.getenv("MSIGHT_KAFKA_TLS_KEY_FILE", None)
        if tls_cert:
            config["ssl_certfile"] = tls_cert
        if tls_key:
            config["ssl_keyfile"] = tls_key
    elif sasl_mechanism:
        # SASL without TLS uses SASL_PLAINTEXT protocol
        config["security_protocol"] = "SASL_PLAINTEXT"
    
    return config
