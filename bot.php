<?php
use Github\Api\Notification;
use Github\Client;

include "vendor/autoload.php";
require "config.php";

/** @var  $client */
$client = new Client();

// Authenticate with token instead of user & pass, this is safer.
$client->authenticate(CCX_OAUTH_TOKEN,null,Client::AUTH_HTTP_TOKEN);

// Get the newest notifications
$notifications = $client->notifications()->all();

foreach($notifications as $notification){
    // Verify repository
    if($notification["repository"]["full_name"] === CCX_REPO_OWNER.'/'.CCX_REPO_NAME){
        // Get problem/PR
        $urlParts = explode("/",$notification["subject"]["url"]);
        $problemNr= intval($urlParts[sizeof($urlParts)-1]);
        // Get type
        $type = $notification["subject"]["type"];

        $first_comment = null;
        $comments = [];

        switch($type){
            case "Issue":
                // Get issue
                $comments = $client->issues()->comments()->all(CCX_REPO_OWNER,CCX_REPO_NAME,$problemNr);
                $first_comment = $client->issues()->show(CCX_REPO_OWNER,CCX_REPO_NAME,$problemNr);
                break;
            case "":
                // TODO: do same for pull request
                break;
            default:
                break;
        }

        if($first_comment === null){
            continue;
        }

        // Go from end to comments up to the first, check for mentions
        foreach($comments as $comment){
            if(strpos($comment["body"],"@".BOT_USERNAME) === false){
                continue;
            }
            // Mention found
            var_dump($comment);
        }

        //var_dump($first_comment);
        //var_dump($comments);
    }
}

$client->notifications()->markRead(new DateTime());