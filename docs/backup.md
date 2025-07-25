Wingfit uses a SQLite database to store the data.

To back up your data, follow these simple steps:
1. **Stop the container**
```bash
# Look for Wingfit container
$ docker ps

$ docker stop <wingfit_container_id>
```

2. **Copy the SQLite database file**
```bash
$ cp /path/to/wingfit/storage/wingfit.sqlite /path/to/backups/wingfit.sqlite.bak
```

3. **Restart the container**

> [!TIP]
> To restore your data, simply copy the `wingfit.sqlite` file back into the `storage` directory.