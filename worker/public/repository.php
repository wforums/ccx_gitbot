<?php
/**
 * Created by PhpStorm.
 * User: Willem
 */
include_once "../private/variables.php";

$command = "INVALID COMMAND";
// This script handles only POST requests that have the necessary variables set and that have a valid HMAC!
if(isset($_POST["github"]) && isset($_POST["folder"]) && isset($_POST["action"]) && isset($_POST["hmac"])){
    // Verify HMAC
    $data = "github=".urlencode($_POST["github"])."&folder=".urlencode($_POST["folder"])."&action=".urlencode($_POST["action"]);
    $hmac = hash_hmac("sha256",$data,HMAC_KEY);
    if($hmac === $_POST["hmac"]){
        // Process request
        switch($_POST["action"]){
            case "add":
                // Clone given repository in given folder
                $cmd = "git clone ".escapeshellarg($_POST["github"])." ".escapeshellarg($_POST["folder"])." > /home/willem/worker/log.txt 2>&1 &";
                exec($cmd);
                $command = "OK";
                break;
            case "remove":
                // Remove given repository (in given folder) from the system
                $cmd = "rm -rf ".escapeshellarg($_POST["folder"])." > /home/willem/worker/log.txt 2>&1 &";
                exec($cmd);
                $command = "OK";
                break;
            default:
                break;
        }
    }
}
echo $command;
exit();