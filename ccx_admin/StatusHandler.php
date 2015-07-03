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
        return ($p->execute() !== false);
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
        $prep = $this->pdo->prepare("SELECT id FROM tests WHERE token = :token AND finished = 0 LIMIT 1;");
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
                    $this->save_status($id,$_POST["status"],$_POST["message"]);
                    break;
                case Status::$FINALIZED:
                case Status::$ERROR:
                    $this->save_status($id,$_POST["status"],$_POST["message"]);
                    $this->mark_finished($id);
                    // TODO: report back to github
                    break;
                default:
                    break;
            }
        }
        return $result;
    }

    public function handle_upload($id){
        $result = "INVALID COMMAND";
        // TODO: finish

        return $result;
    }
}