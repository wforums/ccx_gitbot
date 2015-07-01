<?php
/**
 * Created by PhpStorm.
 * User: Willem
 */
use org\ccextractor\githubbot\StatusHandler;

include_once "variables.php";

$statusHandler = new StatusHandler(CCX_SQLITE_DB_NAME);

$command = "INVALID COMMAND";
// This script handles only POST requests that have a type parameter and a token set, AND has the correct user agent
if($_SERVER['HTTP_USER_AGENT'] === CCX_USER_AGENT) {
    if (isset($_POST["type"]) && isset($_POST["token"])) {
        $id = $statusHandler->validate_token($_POST["token"]);
        if ($id > -1) {
            switch ($_POST["type"]) {
                case "progress":
                    $command = $statusHandler->handle_progress($id);
                    break;
                case "upload":
                    $command = $statusHandler->handle_upload($id);
                    break;
                default:
                    break;
            }
        }
    }
}
echo $command;
$statusHandler->finish();
exit();