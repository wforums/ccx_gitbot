<?php

namespace org\ccextractor\githubbot;


use SQLite3;

/**
 * Class StatusHandler handles an incoming request and takes care of storing/updating the database, as well as launching
 * another VM instance if necessary by calling the python script.
 *
 * @author Willem Van Iseghem
 * @package org\ccextractor\githubbot
 */
class StatusHandler {
    private $sqlite;
    private $pythonScript;

    function __construct($database, $pythonScript)
    {
        $this->sqlite = new SQLite3($database);
        $this->pythonScript = $pythonScript;
    }

    private function save_status($id,$status,$message){
        $p = $this->sqlite->prepare("INSERT INTO messages VALUES (NULL, :test_id, date('now'), :status, :message);");
        $p->bindParam(":test_id",$id,SQLITE3_INTEGER);
        $p->bindParam(":status",$status,SQLITE3_TEXT);
        $p->bindParam(":message",$message,SQLITE3_TEXT);
        return ($p->execute() !== false);
    }

    private function mark_finished($id)
    {
        $p = $this->sqlite->prepare("UPDATE tests SET finished = 1 WHERE id = :id");
        $p->bindParam(":id",$id,SQLITE3_INTEGER);
        if ($p->execute() !== false) {
            $p = $this->sqlite->prepare("DELETE FROM queue WHERE test_id = :test_id LIMIT 1");
            $p->bindParam(":test_id", $id, SQLITE3_INTEGER);
            if($p->execute() !== false){
                // If there's still one or multiple items left in the queue, we'll need to give the python script a
                // kick so it processes the next item.
                $remaining = $this->sqlite->query("SELECT COUNT(*) AS 'left' FROM queue");
                if($remaining !== false && $remaining !== true){
                    $data = $remaining->fetchArray(SQLITE3_ASSOC);
                    if($data['left'] > 0){
                        // Call python script
                        exec("python ".$this->pythonScript." &");
                    }
                }
            }
        }
    }

    public function validate_token($token){
        $prep = $this->sqlite->prepare("SELECT id FROM tests WHERE token = :token AND finished = 0 LIMIT 1;");
        $prep->bindParam(":token", $token, SQLITE3_TEXT);
        $result = $prep->execute();
        if($result !== false){
            $data = $result->fetchArray(SQLITE3_ASSOC);
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


        return $result;
    }

    public function finish()
    {
        $this->sqlite->close();
    }
}