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
    echo '<h1>Admin panel</h1>';
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
        switch($_GET["action"]){
            case "vboxqueue":
                echo '<h2>Current VBox queue</h2>';
                $stmt = $pdo->query("SELECT t.* FROM test_queue q JOIN test t ON q.test_id = t.id ORDER BY t.id ASC;");
                if($stmt !== false){
                    $data = $stmt->fetchAll();
                    if(sizeof($data) > 0) {
                        echo '<table><tr><th>ID</th><th>GitHub</th></tr>';
                        foreach($data as $row){
                            echo '<tr><td>'.$row['id'].'</td><td>'.$row['repository'].'</td></tr>';
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
                echo '<h2>Current local queue</h2>';
                $stmt = $pdo->query("SELECT t.* FROM local_queue q JOIN test t ON q.test_id = t.id ORDER BY t.id ASC;");
                if($stmt !== false){
                    $data = $stmt->fetchAll();
                    if(sizeof($data) > 0) {
                        echo '<table><tr><th>ID</th><th>GitHub</th></tr>';
                        foreach($data as $row){
                            echo '<tr><td>'.$row['id'].'</td><td>'.$row['repository'].'</td></tr>';
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
                        echo '<table><tr><th>Test
                        ID</th><th>Time</th><th>Type</th><th>Requested
                        by</th><th>Link to comment</th></tr>';
                        foreach($data as $row){
                            echo '<tr><td>'.$row['test_id'].'</td><td>'
                            .$row['time'].'</td><td>'.htmlentities
                            ($row['type']).'</td><td>'.htmlentities
                            ($row['requester']).'</td><td>'.htmlentities
                            ($row['link']).'</td></tr>';
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
} else {
?>
    <h1>Login required</h1>
    <p>You need to be logged in to see the admin panel</p>
    <form method="post" action="admin.php">
        <p>Password: <input type="password" name="password" /> <input type="submit" value="Log in" /></p>
    </form>
<?php
}