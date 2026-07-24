import psycopg2
import sys

password = 'Flux@2.5.6!'
ref = 'rzumenyhdodfqjkelzlo'

regions = [
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ap-east-1', 'ap-southeast-1', 'ap-northeast-1', 'ap-northeast-2',
    'ap-south-1', 'ap-southeast-2', 'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1',
    'sa-east-1'
]

for region in regions:
    host = f"aws-0-{region}.pooler.supabase.com"
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=f"postgres.{ref}",
            password=password,
            host=host,
            port="6543",
            connect_timeout=3
        )
        print(f"SUCCESS: {region}")
        conn.close()
        sys.exit(0)
    except Exception as e:
        pass

print("FAILED_ALL")
