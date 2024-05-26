#!/bin/bash

# Function to install MariaDB on Ubuntu/Raspberry Pi OS
install_mariadb_debian() {
    sudo apt update
    sudo apt install -y mariadb-server
    sudo systemctl start mariadb
    sudo systemctl enable mariadb
}

# Function to install MariaDB on Fedora
install_mariadb_fedora() {
    sudo dnf install -y mariadb-server
    sudo systemctl start mariadb
    sudo systemctl enable mariadb
}

# Function to setup the database, user and table
setup_database() {
    sudo mysql -e "CREATE DATABASE IF NOT EXISTS ghostwalks;"
    sudo mysql -e "CREATE USER IF NOT EXISTS 'ghost'@'localhost' IDENTIFIED WITH mysql_native_password BY 'walks';"
    sudo mysql -e "GRANT ALL PRIVILEGES ON ghostwalks.* TO 'ghost'@'localhost';"
    sudo mysql -e "FLUSH PRIVILEGES;"
    sudo mysql -e "USE ghostwalks; CREATE TABLE IF NOT EXISTS positions (id INT AUTO_INCREMENT PRIMARY KEY, x FLOAT, y FLOAT,tagname VARCHAR(30), timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
}

# Check for the distribution and install MariaDB accordingly
if [ -f /etc/debian_version ]; then
    if ! command -v mariadb > /dev/null 2>&1; then
        echo "MariaDB not detected. Installing MariaDB..."
        install_mariadb_debian
    else
        echo "MariaDB is already installed."
    fi
elif [ -f /etc/fedora-release ]; then
    if ! command -v mariadb > /dev/null 2>&1; then
        echo "MariaDB not detected. Installing MariaDB..."
        install_mariadb_fedora
    else
        echo "MariaDB is already installed."
    fi
else
    echo "Unsupported OS."
    exit 1
fi

# Setup the database, user and table
echo "Setting up the database and table..."
setup_database

echo "Setup complete."
