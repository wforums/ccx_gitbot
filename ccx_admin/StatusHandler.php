<?php

namespace org\ccextractor\githubbot;

use PDO;
use PDOException;

/**
 * Class StatusHandler handles an incoming request and takes care of storing/updating the database, as well as launching
 * another VM instance if necessary by calling the python script.
 *
 * @author Willem Van Iseghem
 * @package org\ccextractor\githubbot
 */
class StatusHandler {
    /**
     * @var PDO
     */
    private $pdo;
    /**
     * @var string
     */
    private $pythonScript;

    function __construct($dsn,$username,$password, $pythonScript)
    {
        $this->pdo = new PDO($dsn,$username,$password, [
            PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8",
            PDO::ATTR_PERSISTENT => true
        ]);
        $this->pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $this->pythonScript = $pythonScript;
    }

    private function save_status($id,$status,$message){
        $p = $this->pdo->prepare("INSERT INTO test_progress VALUES (NULL, :test_id, NOW(), :status, :message);");
        $p->bindParam(":test_id",$id,PDO::PARAM_INT);
        $p->bindParam(":status",$status,PDO::PARAM_STR);
        $p->bindParam(":message",$message,PDO::PARAM_STR);
        return ($p->execute() !== false)?"OK":"ERROR";
    }

    private function mark_finished($id)
    {
        if($this->pdo->beginTransaction()){
            try {
                $p = $this->pdo->prepare("UPDATE test SET finished = 1 WHERE id = :id");
                $p->bindParam(":id",$id,PDO::PARAM_INT);
                $p->execute();
                $p = $this->pdo->prepare("DELETE FROM test_queue WHERE test_id = :test_id LIMIT 1");
                $p->bindParam(":test_id", $id, PDO::PARAM_INT);
                $p->execute();
                $this->pdo->commit();
                // If there's still one or multiple items left in the queue, we'll need to give the python script a
                // kick so it processes the next item.
                $remaining = $this->pdo->query("SELECT COUNT(*) AS 'left' FROM test_queue");
                if($remaining !== false){
                    $data = $remaining->fetch();
                    if($data['left'] > 0){
                        // Call python script
                        exec("python ".$this->pythonScript." &");
                    }
                }
            } catch(PDOException $e){
                $this->pdo->rollBack();
            }
        }
    }

    public function validate_token($token){
        $prep = $this->pdo->prepare("SELECT id FROM test WHERE token = :token AND finished = 0 LIMIT 1;");
        $prep->bindParam(":token", $token, PDO::PARAM_STR);
        if($prep->execute() !== false){
            $data = $prep->fetch();
            return $data['id'];
        }
        return -1;
    }

    public function handle_progress($id) {
        $result = "INVALID COMMAND";
        // Validate further necessary parameters (status, message)
        if(isset($_POST["status"]) && isset($_POST["message"])){
            switch($_POST["status"]){
                case Status::$PREPARATION:
                case Status::$RUNNING:
                case Status::$FINALIZATION:
                    $result = $this->save_status($id,$_POST["status"], $_POST["message"]);
                    break;
                case Status::$FINALIZED:
                case Status::$ERROR:
                    $result = $this->save_status($id,$_POST["status"], $_POST["message"]);
                    $this->mark_finished($id);
                    // TODO: report back to github
                    break;
                default:
                    break;
            }
        }
        return $result;
    }

    /**
     * Borrowed from http://stackoverflow.com/questions/834303/startswith-and-endswith-functions-in-php
     *
     * @param string $haystack The string to search in.
     * @param string $needle The string to search
     *
     * @return bool True if found, false otherwise.
     */
    private function endsWith($haystack, $needle) {
        // search forward starting from end minus needle length characters
        return $needle === "" || (($temp = strlen($haystack) - strlen($needle)) >= 0 && strpos($haystack, $needle, $temp) !== FALSE);
    }

    public function handle_upload($id){
        $result = "INVALID COMMAND";
        // Check if a file was provided
        if(array_key_exists("html",$_FILES)){
            // File data
            $data = $_FILES["html"];
            // Do a couple of basic checks. We expect html
            if($this->endsWith($data["name"],".html") && $data["type"] === "text/html" && $data["error"] === UPLOAD_ERR_OK){
                // Create new folder for id if necessary
                $dir = "reports/".$id."/";
                if(!file_exists($dir)){
                    mkdir($dir);
                }
                // Copy file to the directory
                move_uploaded_file($data["tmp_name"],$dir.basename($data["name"]));
                $result = "OK";
            } else {
                // Delete temp file
                @unlink($data["tmp_name"]);
                $result = "FAIL";
            }
        }
        return $result;
    }
}