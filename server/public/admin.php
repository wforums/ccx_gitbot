<?php
session_start();

include "../private/variables.php";

if(!isset($_SESSION["login"])) {
    $_SESSION["login"] = false;
}
if(isset($_POST["password"])){
    // Validate password
    if($_POST["password"] === ADMIN_PASSWORD){
        $_SESSION["login"] = true;
    }
}
if(isset($_GET["action"]) && $_GET["action"] === "logout"){
    $_SESSION["login"] = false;
}
if($_SESSION["login"]) {
    echo '<html><head><link rel="stylesheet" href="layout.css"></head><body><h1>Admin panel</h1>';
    if (!isset($_GET["action"])) {
?>
    <p>Please choose an action:</p>
    <ul>
        <li><a href="admin.php?action=vboxqueue">Show the current VBox queue</a></li>
        <li><a href="admin.php?action=localqueue">Show the local queue</a></li>
        <li><a href="admin.php?action=history">Show the command history</a></li>
        <li><a href="admin.php?action=logout">Logout</a></li>
    </ul>
<?php
    } else {
        $pdo = new PDO(DATABASE_SOURCE_NAME,DATABASE_USERNAME,DATABASE_PASSWORD, [
            PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8",
            PDO::ATTR_PERSISTENT => true
        ]);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        echo '<p><a href="admin.php">Return to overview</a></p>';
        $removeMessage = "The admin removed your request (id {0}) from the queue. Please get in touch to know why.";
        $abortMessage = "The admin aborted your currently running request (id {0}). Please get in touch to know why.";
        switch($_GET["action"]){
            case "vboxqueue":
                $message = "";
                if(isset($_GET["do"]) && isset($_GET["id"])){
                    switch($_GET["do"]){
                        case "remove":
                            if($pdo->beginTransaction()) {
                                try {
                                    $m = $pdo->prepare("INSERT INTO github_queue VALUES (NULL, :test_id, :message);");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->bindParam(":message",str_replace("{0}",intval($_GET["id"]),$removeMessage),PDO::PARAM_STR);
                                    $m->execute();
                                    $m = $pdo->prepare("UPDATE test SET finished = '1' WHERE id = :test_id");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->execute();
                                    $m = $pdo->prepare("DELETE FROM test_queue WHERE test_id = :test_id");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->execute();
                                    $pdo->commit();
                                    $message = intval($_GET["id"])." was removed from the VBox queue!";
                                } catch(PDOException $e){
                                    $pdo->rollBack();
                                    $message = "Failed to remove";
                                }
                            } else {
                                $message = "Failed to begin remove transaction";
                            }
                            break;
                        case "abort":
                            if($pdo->beginTransaction()) {
                                try {
                                    $m = $pdo->prepare("INSERT INTO github_queue VALUES (NULL, :test_id, :message);");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->bindParam(":message",str_replace("{0}",intval($_GET["id"]),$abortMessage),PDO::PARAM_STR);
                                    $m->execute();
                                    $m = $pdo->prepare("UPDATE test SET finished = '1' WHERE id = :test_id");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->execute();
                                    $m = $pdo->prepare("INSERT INTO test_progress VALUES (NULL, :test_id, NOW(), 'error', 'aborted by admin');");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->execute();
                                    $m = $pdo->prepare("DELETE FROM test_queue WHERE test_id = :test_id");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->execute();
                                    $pdo->commit();
                                    $message = intval($_GET["id"])." will be aborted!";
                                    // Bot will automatically turn off the VM in <= 5 minutes
                                } catch(PDOException $e){
                                    $pdo->rollBack();
                                    $message = "Failed to abort";
                                }
                            } else {
                                $message = "Failed to begin abort transaction";
                            }
                            break;
                        default:
                            break;
                    }
                }
                echo '<h2>Current VBox queue</h2>';
                echo '<p>'.$message.'</p>';
                $stmt = $pdo->query("SELECT t.id, t.repository, p.`time` FROM test_queue q JOIN test t ON q.test_id = t.id LEFT JOIN test_progress p ON q.`test_id` = p.`test_id` GROUP BY t.id ORDER BY t.`id`, p.`id` ASC;");
                if($stmt !== false){
                    $data = $stmt->fetchAll();
                    if(sizeof($data) > 0) {
                        echo '<table><tr><th>ID</th><th>GitHub</th><th>Started on</th><th>Manage</th></tr>';
                        foreach($data as $row){
                            echo '<tr>';
                            echo '<td><a href="view.php?id='.$row['id'].'">'.$row['id'].'</a></td>';
                            echo '<td>'.$row['repository'].'</td>';
                            if(is_null($row['time'])){
                                echo '<td>Queued</td>';
                                echo '<td><input type="button" value="Remove" onclick="window.location.href=\'admin.php?action=vboxqueue&do=remove&id='.$row['id'].'\';" /></td>';
                            } else {
                                echo '<td>'.$row['time'].'</td>';
                                echo '<td><input type="button" value="Abort" onclick="window.location.href=\'admin.php?action=vboxqueue&do=abort&id='.$row['id'].'\';" /></td>';
                            }
                            echo '</tr>';
                        }
                        echo '</table>';
                    } else {
                        echo '<p>No entries in the queue</p>';
                    }
                } else {
                    echo '<p>No entries in the queue (false)</p>';
                }
                break;
            case "localqueue":
                $message = "";
                if(isset($_GET["do"]) && isset($_GET["id"])){
                    switch($_GET["do"]){
                        case "remove":
                            if($pdo->beginTransaction()) {
                                try {
                                    $m = $pdo->prepare("INSERT INTO github_queue VALUES (NULL, :test_id, :message);");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->bindParam(":message",str_replace("{0}",intval($_GET["id"]),$removeMessage),PDO::PARAM_STR);
                                    $m->execute();
                                    $m = $pdo->prepare("UPDATE test SET finished = '1' WHERE id = :test_id");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->execute();
                                    $m = $pdo->prepare("DELETE FROM local_queue WHERE test_id = :test_id");
                                    $m->bindParam(":test_id",$_GET["id"],PDO::PARAM_INT);
                                    $m->execute();
                                    $pdo->commit();
                                    $message = intval($_GET["id"])." was removed from the local queue!";
                                } catch(PDOException $e){
                                    $pdo->rollBack();
                                    $message = "Failed to remove";
                                }
                            } else {
                                $message = "Failed to begin remove transaction";
                            }
                            break;
                        default:
                            break;
                    }
                }
                echo '<h2>Current local queue</h2>';
                echo '<p>'.$message.'</p>';
                $stmt = $pdo->query("SELECT t.id, t.repository, p.`time` FROM local_queue q JOIN test t ON q.test_id = t.id LEFT JOIN test_progress p ON q.`test_id` = p.`test_id` GROUP BY t.id ORDER BY t.`id`, p.`id` ASC;");
                if($stmt !== false){
                    $data = $stmt->fetchAll();
                    if(sizeof($data) > 0) {
                        echo '<table><tr><th>ID</th><th>GitHub</th><th>Started on</th><th>Manage</th></tr>';
                        foreach($data as $row){
                            echo '<tr>';
                            echo '<td><a href="view.php?id='.$row['id'].'">'.$row['id'].'</a></td>';
                            echo '<td>'.$row['repository'].'</td>';
                            if(is_null($row['time'])){
                                echo '<td>Queued</td>';
                                echo '<td><input type="button" value="Remove" onclick="window.location.href=\'admin.php?action=localqueue&do=remove&id='.$row['id'].'\';" /></td>';
                            } else {
                                echo '<td>'.$row['time'].'</td>';
                                echo '<td>&nbsp;</td>';
                            }
                            echo '</tr>';
                        }
                        echo '</table>';
                    } else {
                        echo '<p>No entries in the queue</p>';
                    }
                } else {
                    echo '<p>No entries in the queue (false)</p>';
                }
                break;
            case "history":
                echo '<h2>History of commands</h2>';
                $stmt = $pdo->query("SELECT * FROM cmd_history ORDER BY id DESC LIMIT 250;");
                if($stmt !== false){
                    $data = $stmt->fetchAll();
                    if(sizeof($data) > 0) {
                        echo '<table><tr><th>Time</th><th>Command</th><th>Requested
                        by</th><th>Link to comment</th></tr>';
                        foreach($data as $row){
                            echo '<tr><td>'
                            .$row['time'].'</td><td>'.htmlentities
                            ($row['type']).'</td><td>'.htmlentities
                            ($row['requester']).'</td><td><a href="'.htmlentities
                            ($row['link']).'">GitHub comment</a></td></tr>';
                        }
                        echo '</table>';
                    } else {
                        echo '<p>No entries in the history</p>';
                    }
                } else {
                    echo '<p>No entries in the history (false)</p>';
                }
                break;
            default:
                break;
        }
    }
    echo '</body></html>';
} else {
?>
    <h1>Login required</h1>
    <p>You need to be logged in to see the admin panel</p>
    <form method="post" action="admin.php">
        <p>Password: <input type="password" name="password" /> <input type="submit" value="Log in" /></p>
    </form>
<?php
}