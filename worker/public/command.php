<?php
/**
 * Created by PhpStorm.
 * User: Willem
 */

include_once "../private/variables.php";

$command = "INVALID COMMAND";
// This script handles only POST requests that have a token set, AND has the correct user agent
if ($_SERVER['HTTP_USER_AGENT'] === CCX_USER_AGENT_C) {
    if (isset($_POST["token"])) {
        // We can pull the data from the server now. Data will return in json
        $ch = curl_init();

        curl_setopt($ch, CURLOPT_URL, MASTER_SERVER_URL);
        curl_setopt($ch, CURLOPT_USERAGENT, CCX_USER_AGENT_C);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1); // Need to return the result to the variable
        curl_setopt($ch, CURLOPT_POST, true);
        // Add token as post variable
        curl_setopt($ch, CURLOPT_POSTFIELDS, ['token' => $_POST['token']]);

        $data = curl_exec($ch);
        curl_close($ch);
        if ($data !== false) {
            $parsed = json_decode($data);
            if ($parsed !== null) {
                // Got valid JSON
                if($parsed["status"] === "success"){
                    // Init shell script with variables
                    exec(TEST_SCRIPT_LOCATION." ".escapeshellarg($parsed["token"]." ".escapeshellarg($parsed["git"]).
                            " ".escapeshellarg($parsed["branch"])." ".escapeshellarg($parsed["commit"])." &"));
                }
            }
        }
    }
}
echo $command;
exit();