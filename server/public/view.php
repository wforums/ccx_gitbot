<?php

include_once "../private/variables.php";

if(isset($_GET["id"])){
    $pdo = new PDO(DATABASE_SOURCE_NAME,DATABASE_USERNAME,DATABASE_PASSWORD, [
        PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8",
        PDO::ATTR_PERSISTENT => true
    ]);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $pdo->prepare("SELECT * FROM test WHERE id= :id LIMIT 1;");
    $stmt->bindParam(":id",$_GET["id"],PDO::PARAM_INT);
    if($stmt->execute()){
        $testEntry = $stmt->fetch();
        if($testEntry === false){
            // No id like this exists
            echo "Invalid id";
        } else {
            $stmt = $pdo->prepare("SELECT * FROM test_progress WHERE test_id = :id ORDER BY id ASC;");
            $stmt->bindParam(":id",$testEntry["id"],PDO::PARAM_INT);
            if($stmt->execute()){
                $data = $stmt->fetchAll();
                if(sizeof($data) >= 1){
                    echo '<html><head><link href="layout.css" rel="stylesheet" /></head><body>';
                    echo "<h1>Progress for test request</h1>";
                    $url = str_replace(".git","",str_replace('git://','https://',$testEntry["repository"]));
                    switch($testEntry["type"]){
                        case "Commit":
                            $url .= "/commit/".$testEntry["commit_hash"];
                            echo "<p>Testing repository ".htmlentities($testEntry["repository"])." in branch ".htmlentities($testEntry["branch"]).' for commit <a href="'.htmlentities($url).'">'.htmlentities($testEntry["commit_hash"])."</a></p>";
                            break;
                        case "PullRequest":
                            $url .= "/pull/".$testEntry["commit_hash"];
                            echo "<p>Testing repository ".htmlentities($testEntry["repository"]).' for <a href="'.htmlentities($url).'">pull request '.htmlentities($testEntry["commit_hash"])."</a></p>";
                            break;
                        default:
                            echo "Unknown test type!";
                            break;
                    }
                    echo "<table>";
                    echo "<tr><th>Time</th><th>Status</th><th>Message</th></tr>";
                    foreach($data as $row){
                        echo "<tr><td>".$row['time']."</td><td>".htmlentities($row["status"])."</td><td>".htmlentities($row["message"])."</td></tr>";
                    }
                    echo "</table>";
                    if($testEntry["finished"] === "1"){
                        echo '<p><a class="button" href="reports/'.$testEntry['id'].'/">Go to the results</a></p>';
                        echo '<p><strong>WARNING! The result files have been auto-generated and could possibly contain malware*, so please use caution.</strong></p>';
                        echo '<p>(* That is, if someone is so unkind to abuse the functionality of the bot)</p>';
                    }
                    echo '</body></html>';
                } else {
                    echo "Still in the waiting queue. Please return later";
                }
            }
        }
    } else {
        echo "Invalid id";
    }
} else {
    echo "No id specified";
}