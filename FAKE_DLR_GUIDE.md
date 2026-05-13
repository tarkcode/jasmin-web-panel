# Fake DLR Implementation Guide

## Overview

A complete **Fake DLR (Delivery Report)** system that routes a configurable percentage of SMS traffic to internal delivery simulation instead of actual vendors.

**Example:** With 30% Fake DLR configuration:
- 10 messages sent → 3 go to Fake DLR (simulated), 7 go to real vendor
- Customer sees "DELIVRD" for all 10 messages
- Only 7 were actually sent → 30% cost savings

## Quick Start

### 1. Run Migration
```bash
python manage.py migrate
```

### 2. Initialize Demo
```bash
python manage.py fake_dlr init_demo
```

### 3. Start Connector
```bash
python manage.py fake_dlr start_connector --cid=fake_demo_high
```

### 4. Configure Route
- Open Django Admin: `http://your-server/admin/`
- Go to **Core → Fake DLR Routes**
- Create route with desired percentage (e.g., 30%)

### 5. View Statistics
```bash
python manage.py fake_dlr statistics
```

## Testing on AWS Server

### Connect to Server
```bash
ssh -i jasmin-web-key.pem ubuntu@16.16.92.247
cd jasmin-web-panel
```

### Run Migration
```bash
docker compose exec jasmin-web python manage.py migrate
```

### Initialize Demo
```bash
docker compose exec jasmin-web python manage.py fake_dlr init_demo
```

### Start Connector
```bash
docker compose exec jasmin-web python manage.py fake_dlr start_connector \
  --cid=fake_demo_high \
  --rabbitmq-host=rabbitmq \
  --rabbitmq-port=5672 \
  --rabbitmq-user=guest \
  --rabbitmq-pass=guest
```

### View Statistics
```bash
docker compose exec jasmin-web python manage.py fake_dlr statistics
```

### Access Admin
- URL: http://16.16.92.247:8999/admin/
- Configure routes in **Core → Fake DLR Routes**

## CLI Commands

```bash
# List connectors
python manage.py fake_dlr list_connectors

# List routes
python manage.py fake_dlr list_routes

# Create connector
python manage.py fake_dlr create_connector \
  --cid=my_conn --name="My Connector" \
  --success-rate=95 --min-delay=5 --max-delay=15

# Start connector
python manage.py fake_dlr start_connector --cid=my_conn

# Stop connector
python manage.py fake_dlr stop_connector --cid=my_conn

# View statistics
python manage.py fake_dlr statistics
```

## API Endpoints

### Connectors
- `GET /api/fake-dlr-connectors/` - List all
- `POST /api/fake-dlr-connectors/` - Create
- `GET /api/fake-dlr-connectors/{cid}/` - Get details
- `PUT /api/fake-dlr-connectors/{cid}/` - Update
- `DELETE /api/fake-dlr-connectors/{cid}/` - Delete
- `POST /api/fake-dlr-connectors/{cid}/start/` - Start
- `POST /api/fake-dlr-connectors/{cid}/stop/` - Stop

### Routes
- `GET /api/fake-dlr-routes/` - List all
- `GET /api/fake-dlr-routes/statistics/` - Get statistics

## Configuration Examples

### Testing (100% Fake)
```python
# Connector
{
    'cid': 'fake_test',
    'success_rate': 100,
    'instant_response': True
}

# Route
{
    'fake_dlr_percentage': 100,
    'filter_user_uid': 'test_user'
}
```

### Production (30% Fake)
```python
# Connector
{
    'cid': 'fake_prod',
    'success_rate': 95,
    'min_delay': 5,
    'max_delay': 15
}

# Route
{
    'fake_dlr_percentage': 30,
    'real_connector_cid': 'vendor_a'
}
```

## Use Cases

1. **Testing** - 100% fake for development
2. **Cost Reduction** - 20-40% fake for production
3. **Grey Routes** - 50-70% fake for low-quality traffic
4. **Promotional** - 30-50% fake for non-critical messages

## Troubleshooting

### Connectors not starting
- Check RabbitMQ is running: `docker compose ps rabbitmq`
- Verify credentials in start command
- Check logs: `docker compose logs jasmin-web`

### Messages not routing to Fake DLR
- Verify route is enabled in Django Admin
- Check connector is enabled
- Verify percentage > 0

### Statistics not updating
- Ensure messages are flowing through system
- Check database connection
- Verify routes are properly configured

## Architecture

```
Customer → SMS Gateway → Routing Engine
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
              Fake DLR (X%)      Real Vendor (Y%)
                    ↓                   ↓
            Internal DLR          Actual SMS + DLR
                    ↓                   ↓
                    └─────────┬─────────┘
                              ↓
                         Customer
```

## Files Created

**Core Implementation:**
- `main/core/fake_dlr.py` - Core engine
- `main/core/fake_dlr_router.py` - Routing logic
- `main/core/models/fake_dlr.py` - Database models
- `main/core/admin/fake_dlr.py` - Django admin
- `main/api/views/fake_dlr.py` - REST API
- `main/core/management/commands/fake_dlr.py` - CLI commands
- `main/core/migrations/0002_fake_dlr_models.py` - Migration

**Test Script:**
- `test_fake_dlr_simple.py` - Simple test script

## Database Tables

- `tbl_fake_dlr_connectors` - Connector configurations
- `tbl_fake_dlr_routes` - Route configurations with traffic splitting

## Security

- Only administrators should access Fake DLR configuration
- Use Django permissions to restrict access
- Monitor usage through activity logs
- Consider customer disclosure requirements

## Support

For issues or questions:
- Check Django Admin for configuration
- Review logs: `docker compose logs jasmin-web`
- Check RabbitMQ: `docker compose logs rabbitmq`
- Consult Jasmin SMS Gateway documentation
