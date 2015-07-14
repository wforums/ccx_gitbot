<?php
/**
 * Created by PhpStorm.
 * User: Willem
 */
use org\ccextractor\githubbot\FetchHandler;

include_once "../private/variables.php";
include_once "../private/src/githubbot/FetchHandler.php";

$command = "INVALID COMMAND";
// This script handles only POST requests that have a token set, AND has the correct user agent
if ($_SERVER['HTTP_USER_AGENT'] === CCX_USER_AGENT_S) {
    if (isset($_POST["token"])) {
        $fetch = new FetchHandler(DATABASE_SOURCE_NAME,DATABASE_USERNAME,DATABASE_PASSWORD);
        return $fetch->handle($_POST["token"]);
    }
}
echo $command;
exit();