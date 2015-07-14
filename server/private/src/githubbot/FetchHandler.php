<?php
/**
 * Created by PhpStorm.
 * User: Willem
 */
namespace org\ccextractor\githubbot;

use PDO;

class FetchHandler
{
    /**
     * @var PDO
     */
    private $pdo;

    function __construct($dsn,$username,$password)
    {
        $this->pdo = new PDO($dsn,$username,$password, [
            PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8",
            PDO::ATTR_PERSISTENT => true
        ]);
        $this->pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    }

    public function handle($token)
    {
        $result = ["status" => "failed"];

        $stmt = $this->pdo->prepare("SELECT t.token, t.branch, t.commit_hash, l.local FROM test t JOIN local_repos l ON t.repository = l.github WHERE t.token = :token AND t.`finished` = 0 LIMIT 1;");
        $stmt->bindParam(":token",$token,PDO::PARAM_STR);

        if($stmt->execute()){
            if($stmt->rowCount() === 1){
                $data = $stmt->fetch();
                $result["status"] = "success";
                $result["token"] = $data["token"];
                $result["branch"] = $data["branch"];
                $result["commit"] = $data["commit_hash"];
                $result["git"] = $data["local"];
            }
        }
        return json_encode($result);
    }
}