<?php

namespace org\ccextractor\githubbot;

use DOMDocument;
use DOMNode;
use Katzgrau\KLogger\Logger;
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
    /**
     * @var string
     */
    private $workerScript;
    /**
     * @var string
     */
    private $reportFolder;
    /**
     * @var string
     */
    private $base_URL;
    /**
     * @var Logger
     */
    private $logger;

    /**
     * @param $dsn
     * @param $username
     * @param $password
     * @param $pythonScript
     * @param $workerScript
     * @param $uploadFolder
     * @param $base_url
     * @param Logger $logger
     */
    function __construct($dsn,$username,$password, $pythonScript, $workerScript, $uploadFolder,$base_url, Logger $logger)
    {
        $this->pdo = new PDO($dsn,$username,$password, [
            PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8",
            PDO::ATTR_PERSISTENT => true
        ]);
        $this->pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $this->pythonScript = $pythonScript;
        $this->workerScript = $workerScript;
        $this->reportFolder = $uploadFolder;
        $this->base_URL = $base_url;
        $this->logger = $logger;
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
                $this->logger->info("Marking id ".$id." as done");
                $p = $this->pdo->prepare("UPDATE test SET finished = 1 WHERE id = :id");
                $p->bindParam(":id",$id,PDO::PARAM_INT);
                $p->execute();
                $p = $this->pdo->prepare("DELETE FROM test_queue WHERE test_id = :test_id LIMIT 1");
                $p->bindParam(":test_id", $id, PDO::PARAM_INT);
                $p->execute();
                if($p->rowCount() === 1) {
                    $this->logger->info("Deleted id from VM queue; checking for more");
                    // If there's still one or multiple items left in the queue, we'll need to give the python script a
                    // kick so it processes the next item.
                    $remaining = $this->pdo->query("SELECT COUNT(*) AS 'left' FROM test_queue");
                    if ($remaining !== false) {
                        $data = $remaining->fetch();
                        if ($data['left'] > 0) {
                            $this->logger->info("Starting python script");
                            // Call python script
                            $cmd = "python ".$this->pythonScript."> ".$this->logger->getLogFilePath()."/python.txt 2>&1 &";
                            $this->logger->debug("Shell command: ".$cmd);
                            exec($cmd);
                            $this->logger->debug("Python script returned");
                        }
                    }
                } else {
                    // Remove on test_queue failed, so it must be local
                    $p = $this->pdo->prepare("DELETE FROM local_queue WHERE test_id = :test_id LIMIT 1");
                    $p->bindParam(":test_id", $id, PDO::PARAM_INT);
                    $p->execute();
                    $this->logger->info("Deleted id from local queue; checking for more");
                    $remaining = $this->pdo->query("SELECT t.`token` FROM local_queue l JOIN test t ON l.`test_id` = t.`id` ORDER BY l.`test_id` ASC LIMIT 1;");
                    if ($remaining !== false && $remaining->rowCount() === 1) {
                        $this->logger->info("Starting shell script");
                        $data = $remaining->fetch();
                        // Call worker shell script
                        $cmd = $this->workerScript." ".escapeshellarg($data["token"])."> ".$this->logger->getLogFilePath()."/shell.txt 2>&1 &";
                        $this->logger->debug("Shell command: ".$cmd);
                        exec($cmd);
                        $this->logger->debug("Shell script returned");
                    }
                }
                $this->pdo->commit();
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
                    $this->queue_github_comment($id,$_POST["status"]);
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
                $dir = $this->reportFolder."/".$id."/";
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

    private function queue_github_comment($id, $status)
    {
        $message = "";
        $overview = "[status](".$this->base_URL."/view.php?id=".$id.")";
        $reports = "[results](".$this->base_URL."/reports/".$id.")";
        switch($status){
            case Status::$FINALIZED:
                // Fetch index.html, parse it and convert to a MD table
                $index = $this->reportFolder."/".$id."/index.html";
                if(file_exists($index)){
                    $dom = new DOMDocument();
                    $dom->loadHTMLFile($index);
                    $tables = $dom->getElementsByTagName("table");
                    if($tables->length > 0){
                        $table = $tables->item(0);
                        // Convert table to markdown
                        $md = "";
                        $errors = false;
                        $firstRow = true;
                        /** @var DOMNode $row */
                        foreach($table->childNodes as $row){
                            if($row->hasChildNodes()){
                                $md .= "|";
                                /** @var DOMNode $cell */
                                foreach($row->childNodes as $cell){
                                    if($cell->nodeType === XML_ELEMENT_NODE) {
                                        $bold = "";
                                        if($cell->hasAttributes()){
                                            $attr = $cell->attributes->getNamedItem("class");
                                            if($attr !== null){
                                                if($attr->nodeValue === "red"){
                                                    $bold="**";
                                                    $errors = true;
                                                }
                                            }
                                        }
                                        $md .= " " . $bold . $cell->textContent . $bold . " |";
                                    }

                                }
                                $md .= "\r\n";
                                if($firstRow){
                                    $md .= str_replace("- -","---",preg_replace('/[^\|\s]/', '-', $md, -1));
                                    $firstRow = false;
                                }
                            }
                        }
                        if($errors){
                            $md .= "It seems there were some errors. Please check the ".$overview." and ".$reports." page, and verify these.";
                        }
                        $message = "The test suite completed it's run. This is a summary (full info can be found on the ".$overview." page:\r\n\r\n".$md;
                    } else {
                        $message = "The index file contained invalid contents. Please check the ".$overview." page, and get in touch with us in case of an error!";
                    }
                } else {
                    $message = "There is no index file available. Please check the ".$overview." page, and get in touch with us in case of an error!";
                }
                break;
            case Status::$ERROR:
                $message = "An error occurred while running the tests. Please check the ".$overview." page, and correct the error.";
                break;
            default:
                break;
        }
        if($message !== ""){
            $stmt = $this->pdo->prepare("INSERT INTO github_queue VALUES(NULL,:id,:message);");
            $stmt->bindParam(":id",$id,PDO::PARAM_INT);
            $stmt->bindParam(":message",$message,PDO::PARAM_STR);
            $stmt->execute();
        }
    }
}