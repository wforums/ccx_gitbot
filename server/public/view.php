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
                    echo "<p>Testing repository ".htmlentities($testEntry["repository"])." in branch ".htmlentities($testEntry["branch"])." for commit ".htmlentities($testEntry["commit_hash"])."</p>";
                    echo "<table>";
                    echo "<tr><th>Time</th><th>Status</th><th>Message</th></tr>";
                    foreach($data as $row){
                        echo "<tr><td>".$row['time']."</td><td>".htmlentities($row["status"])."</td><td>".htmlentities($row["message"])."</td></tr>";
                    }
                    echo "</table>";
                    if($testEntry["finished"] === "1"){
                        echo '<p><a href="reports/'.$testEntry['id'].'/">Go to the results</a></p>';
                        echo '<p><strong>WARNING! The result files have been auto-generated, and could possibly contain malware*, use caution.</strong></p>';
                        echo '<p>(* Provided someone abuses the functionality of the bot)</p>';
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