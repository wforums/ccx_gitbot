/*!40101 SET NAMES utf8 */;

CREATE DATABASE /*!32312 IF NOT EXISTS*/`ccx_githubbot` /*!40100 DEFAULT CHARACTER SET latin1 */;

USE `ccx_githubbot`;

/*Table structure for table `test` */

DROP TABLE IF EXISTS `test`;

CREATE TABLE `test` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `token` varchar(32) NOT NULL,
  `finished` tinyint(1) NOT NULL DEFAULT '0',
  `repository` text NOT NULL,
  `branch` text NOT NULL,
  `commit_hash` text NOT NULL,
  `type` text NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

/*Table structure for table `cmd_history` */

DROP TABLE IF EXISTS `cmd_history`;

CREATE TABLE `cmd_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `time` datetime NOT NULL,
  `type` varchar(100) NOT NULL,
  `requester` varchar(100) NOT NULL,
  `test_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK_cmd_history_test` (`test_id`),
  CONSTRAINT `FK_cmd_history_test` FOREIGN KEY (`test_id`) REFERENCES `test` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

/*Table structure for table `test_progress` */

DROP TABLE IF EXISTS `test_progress`;

CREATE TABLE `test_progress` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `test_id` int(11) NOT NULL,
  `time` datetime NOT NULL,
  `status` varchar(100) NOT NULL,
  `message` text,
  PRIMARY KEY (`id`),
  KEY `FK_test_progress_test` (`test_id`),
  CONSTRAINT `FK_test_progress_test` FOREIGN KEY (`test_id`) REFERENCES `test` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

/*Table structure for table `test_queue` */

DROP TABLE IF EXISTS `test_queue`;

CREATE TABLE `test_queue` (
  `test_id` int(11) NOT NULL,
  PRIMARY KEY (`test_id`),
  CONSTRAINT `FK_test_queue_test` FOREIGN KEY (`test_id`) REFERENCES `test` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

/*Table structure for table `local_queue` */

DROP TABLE IF EXISTS `local_queue`;

CREATE TABLE `local_queue` (
  `test_id` int(11) NOT NULL,
  PRIMARY KEY (`test_id`),
  CONSTRAINT `FK_local_queue_test` FOREIGN KEY (`test_id`) REFERENCES `test` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

/*Table structure for table `local_repos` */

DROP TABLE IF EXISTS `local_repos`;

CREATE TABLE `local_repos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `github` text NOT NULL,
  `local` text NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

/*Table structure for table `github_queue` */

DROP TABLE IF EXISTS `github_queue`;

CREATE TABLE `github_queue` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `test_id` int(11) NOT NULL,
  `message` text NOT NULL,
  PRIMARY KEY (`id`),
  KEY `FK_github_queue_test` (`test_id`),
  CONSTRAINT `FK_github_queue_test` FOREIGN KEY (`test_id`) REFERENCES `test` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;