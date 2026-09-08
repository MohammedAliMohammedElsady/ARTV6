<!-- 
## Prerequisites

Before starting the deployment, ensure you have:

1. **Docker Engine** (version 20.10 or higher)
2. **Docker Compose** (version 2.0 or higher)
3. **Network Access** to your database server
4. **Database Administrator Access** to create databases and run SQL scripts
5. **SSL Certificates** for DGUM integration (if applicable) -->

## Step 1: Extract and Prepare Files

1. Extract the deployment package:
```bash
tar -xzf artv3-deployment-package.tar.gz
cd artv3-deployment
```

2. Load Docker images:
```bash
# Load ARTV3 and Redis images
docker load < compressed_images.tar
```

3. Verify images are loaded:
```bash
docker images | grep artv3
docker images | grep redis
```

## Step 2: Database Setup

Before configuring ARTV3, you must create the database and run the appropriate schema script for your database provider.

### Create Database

1. **Connect to your database server** using your preferred database client or command line tool.

2. **Create a new database** for ARTV3:

```sql
-- Example for PostgreSQL
CREATE DATABASE artv3_db;

-- Example for MySQL
CREATE DATABASE artv3_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Example for SQL Server
CREATE DATABASE artv3_db;

-- Example for Oracle
CREATE TABLESPACE artv3_ts DATAFILE 'artv3_data.dbf' SIZE 1G AUTOEXTEND ON;
CREATE USER artv3_user IDENTIFIED BY your_password DEFAULT TABLESPACE artv3_ts;
GRANT CONNECT, RESOURCE, DBA TO artv3_user;
```

### Run Database Schema Script

3. **Execute the appropriate SQL script** from the `DB_SCRIPTS/` folder based on your database type:

#### PostgreSQL
```bash
psql -h your-host -U your-username -d artv3_db -f DB_SCRIPTS/ARTV3_POSTGRES_complete_ddl_schema.sql
```

#### MySQL
```bash
mysql -h your-host -u your-username -p artv3_db < DB_SCRIPTS/ARTV3_MYSQL_complete_ddl_schema.sql
```

#### SQL Server
```bash
sqlcmd -S your-host -U your-username -P your-password -d artv3_db -i DB_SCRIPTS/ARTV3_MSSQL_complete_ddl_schema.sql
```

#### Oracle
```bash
sqlplus your-username/your-password@your-host:1521/your-service @DB_SCRIPTS/ARTV3_ORCL_complete_ddl_schema.sql
```

4. **Verify the schema creation** by checking that tables have been created successfully in your database.

## Step 3: Configure Environment Variables



1. Edit the `.env` file with your institution-specific settings:

```bash
# ============================================================================
# INSTITUTION CONFIGURATION
# ============================================================================

# Institution client name (format: DGART{institutionname})
CLIENT_NAME=DGART{YourInstitutionName}

# Container name for ARTV3 application
CONTAINER_NAME=ARTV3_app

# Environment settings
SUPERSET_ENV=production
# Options: debug, development, production

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database connection settings
DATABASE_DIALECT=postgresql+psycopg2
# Options: postgresql+psycopg2, mysql+pymysql, mssql+pymssql, oracle+cx_oracle

DATABASE_HOST=your-database-host
DATABASE_PORT=5432
DATABASE_USER=your-username
DATABASE_PASSWORD=your-password
DATABASE_DB=artv3_db
# Use the database name you created in Step 2


# ============================================================================
# REDIS CONFIGURATION
# ============================================================================

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_CELERY_DB=0
REDIS_RESULTS_DB=1

# ============================================================================
# LICENSE CONFIGURATION
# ============================================================================

# License settings
LICENSE_MAX_USERS=100
LICENSE_WARNING_DAYS=30

# ============================================================================
# DGUM INTEGRATION (Data Gear User Management)
# ============================================================================

# External authentication URL
EXTERNAL_AUTH_URL=https://your-dgum-server:9999

# DGUM API endpoint
POST_URL=/dg-userManagement-console/security/signIn

# Certificate file names (must match files in DGUM_certificates/)
PATH_CRT=your-domain.crt
PATH_KEY=your-domain.key
PATH_VERIFY=your-ca.cer

# ============================================================================
# SMTP EMAIL CONFIGURATION
# ============================================================================

# SMTP server settings for email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_SSL=false
SMTP_USER=your-email@domain.com
SMTP_PASSWORD=your-app-password
SMTP_MAIL_FROM=your-email@domain.com

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================

# Logging level
SUPERSET_LOG_LEVEL=info
# Options: debug, info, warning, error

# Load example data (set to 'no' for production)
SUPERSET_LOAD_EXAMPLES=no

# Admin user credentials (for initial setup)
ADMIN_PASSWORD=your-secure-admin-password
```

## Step 4: Configure DGUM Certificates

1. Place your institution's DGUM certificates in the `DGUM_certificates/` directory:

```bash
# Copy your certificates to the DGUM_certificates directory
cp /path/to/your-domain.crt DGUM_certificates/
cp /path/to/your-domain.key DGUM_certificates/
cp /path/to/your-ca.cer DGUM_certificates/
```

2. Ensure certificate file names match the values in your `.env` file:
   - `PATH_CRT` should match your certificate file
   - `PATH_KEY` should match your private key file
   - `PATH_VERIFY` should match your CA certificate file

## Step 5: Update Docker Compose Configuration

1. Open `docker-compose.yml` and update the image references if needed:

```yaml
x-superset-image: &superset-image your-registry/artv3:latest
```

2. Verify volume mappings and network configuration match your environment.

## Step 6: Deploy ARTV3

1. Start the deployment:
```bash
# Start all services
docker-compose up -d
```

2. Monitor the deployment:
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f ARTV3_app
```

3. Wait for initialization to complete. The first startup may take several minutes as it:
   - Initializes the database schema
   - Creates the admin user
   - Sets up roles and permissions
   - Loads any example data (if enabled)

## Step 7: Verify Deployment

1. **Check Service Health:**
```bash
# Verify all containers are running
docker-compose ps

# Check application logs
docker-compose logs ARTV3_app | tail -20
```

2. **Access the Application:**
   - Open your web browser
   - Navigate to: `http://your-server-ip:9065`
   - Login with: 
     - Username: `admin`
     - Password: `[value from ADMIN_PASSWORD in .env]`

3. **Test Database Connection:**
   - Go to "Data" → "Databases"
   - Click "Test Connection" on your configured database
   - Verify successful connection

4. **Test DGUM Integration (if configured):**
   - Try logging in with a DGUM user account
   - Verify external authentication works correctly

## Troubleshooting

### Common Issues

1. **Container fails to start:**
```bash
# Check logs for error messages
docker-compose logs [service-name]

# Check environment variables
docker-compose config
```

2. **Database connection errors:**
   - Verify database credentials in `.env`
   - Ensure database server is accessible from Docker containers
   - Check firewall settings
   - Verify the database schema was created successfully

3. **Database schema issues:**
   - Ensure you ran the correct SQL script for your database type
   - Check that all tables were created successfully
   - Verify database user has proper permissions

4. **Certificate issues:**
   - Verify certificate files exist in `DGUM_certificates/`
   - Check file permissions (should be readable by Docker)
   - Ensure certificate file names match `.env` configuration


### Useful Commands

```bash
# Restart services
docker-compose restart

# View real-time logs
docker-compose logs -f

# Access container shell
docker-compose exec ARTV3_app bash

# Stop all services
docker-compose down

```

## Maintenance

### Regular Tasks

1. **Backup Database:**
   - Schedule regular backups of your ARTV3 database
   - Include dashboard exports if needed

2. **Monitor Logs:**
```bash
# Check for errors
docker-compose logs ARTV3_app | grep ERROR

# Monitor resource usage
docker stats
```

3. **Update Images:**
   - When new ARTV3 images are available
   - Follow the same image loading process
   - Test in staging environment first

### Security Considerations

1. **Change Default Passwords:**
   - Update the admin password after initial setup
   - Use strong passwords for all accounts

2. **Network Security:**
   - Consider using a reverse proxy (nginx) for SSL termination
   - Restrict network access to necessary ports only

3. **Certificate Management:**
   - Keep DGUM certificates updated
   - Monitor certificate expiration dates

## Support

For technical support or issues:

1. Check the troubleshooting section above
2. Review application logs for error messages
3. Contact DataGear support team with:
   - Error logs
   - Configuration details (sanitized)
   - Steps to reproduce the issue

## Configuration Reference

### Environment Variables Summary

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CLIENT_NAME` | Institution identifier | DGARTDG | Yes |
| `CONTAINER_NAME` | Container name | ARTV3_app | Yes |
| `DATABASE_DIALECT` | Database dialect | - | Yes |
| `DATABASE_HOST` | Database server hostname | - | Yes |
| `DATABASE_USER` | Database username | - | Yes |
| `DATABASE_PASSWORD` | Database password | - | Yes |
| `DATABASE_DB` | Database name | - | Yes |
| `LICENSE_MAX_USERS` | Maximum licensed users | 100 | Yes |
| `EXTERNAL_AUTH_URL` | DGUM server URL | - | If using DGUM |
| `SMTP_HOST` | SMTP server | smtp.gmail.com | If using email |
| `SUPERSET_ENV` | Environment type | production | Yes |

---

**DataGear Analytics Reporting Tool (ARTV3)**  
*Version 3.0*  
*Deployment Guide v1.0*
