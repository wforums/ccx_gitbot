<?php
/**
 * Created by PhpStorm.
 * User: Willem
 *
 * Copy and rename this file to variables.php and fill in the necessary values in order for the script to work
 */
// User agent, must be equal to the user agent in ccx_vmscripts/variables(-sample)
define("CCX_USER_AGENT","My user agent string");
// User agent for reply back, must be equal to the user agent in the command server settings
define("CCX_USER_AGENT_S","My user agent");
// Path to the python vboxmanager script
define("CCX_VBOX_MANAGER","/path/to/vbox/manager.py");
// Path to the runNext script
define("CCX_WORKER","/path/to/runNext");
// MySQL database source name
define("DATABASE_SOURCE_NAME","mysql:dbname=MYDATABASENAME;host=localhost");
// MySQL username
define("DATABASE_USERNAME","MYUSERNAME");
// MySQL password
define("DATABASE_PASSWORD","MYPASSWORD");
// Admin password
define("ADMIN_PASSWORD","The admin password");
// Base URL of the application (without trailing slash)
define("BASE_URL","http://my.domain.here/subfolder");
// The author of the application (don't forget the @ sign if you want to get a notification when someone uses the tool).
define("AUTHOR","@github_name");