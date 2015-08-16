<?php
/**
 * Created by PhpStorm.
 * User: Willem
 *
 * Copy and rename this file to variables.php and fill in the necessary values in order for the script to work
 */
// User agent, must be equal to the user agent in the command server settings
define("CCX_USER_AGENT_C","My username here");
// User agent for reply back, must be equal to the user agent in the command server settings
define("CCX_USER_AGENT_S","My user agent here");
// Location to fetch the data from
define("MASTER_SERVER_URL","http://my.master.server/fetch.php");
// Location of the test script
define("TEST_SCRIPT_LOCATION","/path/to/script/private/runLocal");
// HMAC key, needs to be the same as the command server one.
define("HMAC_KEY","my random hmac key here");