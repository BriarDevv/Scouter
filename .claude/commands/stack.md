Manage the Scouter stack. Accepts an argument: `up`, `down`, or `status`.

If no argument is given, show status.

Commands:
```bash
# Start everything
wsl.exe -d Ubuntu -- bash -c "cd /home/mateo/src/Scouter && make up"

# Stop everything
wsl.exe -d Ubuntu -- bash -c "cd /home/mateo/src/Scouter && make down"

# Check status
wsl.exe -d Ubuntu -- bash -c "cd /home/mateo/src/Scouter && make status"
```

After running, report which services are up and on which ports:
- Dashboard: http://localhost:3000
- API/Swagger: http://localhost:8000/docs
- Flower: http://localhost:5555
