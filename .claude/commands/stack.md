Manage the Scouter stack. Accepts an argument: `up`, `down`, or `status`.

If no argument is given, show status.

Commands:
```bash
# Start everything
make up

# Stop everything
make down

# Check status
make status
```

After running, report which services are up and on which ports:
- Dashboard: http://localhost:3000
- API/Swagger: http://localhost:8000/docs
- Flower: http://localhost:5555
