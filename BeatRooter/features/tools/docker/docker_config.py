DOCKER_CONFIG = {
    'base_images': {
        'python': 'python:3.11-slim',
        'postgresql': 'postgres:15',
        'mysql': 'mysql:8.0',
        'mongodb': 'mongo:6.0',
        'nodejs': 'node:18-alpine',
        'nginx': 'nginx:alpine'
    },
    'default_ports': {
        'flask': 5000,
        'django': 8000,
        'postgresql': 5432,
        'mysql': 3306,
        'mongodb': 27017,
        'nodejs': 3000,
        'react': 3000,
        'vue': 5173
    },
    'common_dependencies': {
        'flask': ['flask', 'python-dotenv', 'gunicorn'],
        'django': ['django', 'gunicorn', 'psycopg2-binary'],
        'postgresql': ['psycopg2-binary'],
        'mysql': ['mysql-connector-python'],
        'mongodb': ['pymongo']
    }
}