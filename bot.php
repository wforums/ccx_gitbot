<?php
include "vendor/autoload.php";

$client = new GitHubClient();
$client->setDebug(true);
$client->setOauthKey(CCX_OAUTH_TOKEN);

var_dump($client->activity);