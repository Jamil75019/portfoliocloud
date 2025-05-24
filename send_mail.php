<?php
// Désactiver l'affichage des erreurs dans la sortie
ini_set('display_errors', 0);
error_reporting(E_ALL);

// Configuration des headers
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Logging function
function logError($message) {
    error_log("[" . date('Y-m-d H:i:s') . "] " . $message . "\n", 0);
}

logError("Début du traitement de la requête");
logError("Méthode: " . $_SERVER['REQUEST_METHOD']);
logError("Content-Type: " . $_SERVER['CONTENT_TYPE']);
logError("User Agent: " . $_SERVER['HTTP_USER_AGENT']);

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    logError("Méthode non autorisée: " . $_SERVER['REQUEST_METHOD']);
    header('Location: /?error=method');
    exit;
}

// Récupérer les données POST
$name = $_POST['name'] ?? '';
$email = $_POST['email'] ?? '';
$message = $_POST['message'] ?? '';

logError("Données reçues - Nom: $name, Email: $email");
logError("Message reçu: $message");

if (empty($name) || empty($email) || empty($message)) {
    logError("Champs manquants dans la requête");
    header('Location: /?error=missing');
    exit;
}

$name = filter_var($name, FILTER_SANITIZE_STRING);
$email = filter_var($email, FILTER_SANITIZE_EMAIL);
$message = filter_var($message, FILTER_SANITIZE_STRING);

logError("Données filtrées - Nom: $name, Email: $email");

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    logError("Format d'email invalide: $email");
    header('Location: /?error=email');
    exit;
}

$to = "jamilmdk.pro@gmail.com";
$subject = "Nouveau message de contact - Portfolio";

// Construction des en-têtes
$headers = array(
    'From' => $email,
    'Reply-To' => $email,
    'X-Mailer' => 'PHP/' . phpversion(),
    'MIME-Version' => '1.0',
    'Content-Type' => 'text/plain; charset=UTF-8'
);

$email_content = "Nouveau message de contact reçu :\n\n";
$email_content .= "Nom : " . $name . "\n";
$email_content .= "Email : " . $email . "\n\n";
$email_content .= "Message :\n" . $message . "\n\n";
$email_content .= "---\n";
$email_content .= "Envoyé depuis le formulaire de contact du portfolio\n";
$email_content .= "Date : " . date('Y-m-d H:i:s') . "\n";
$email_content .= "IP : " . $_SERVER['REMOTE_ADDR'] . "\n";

logError("Tentative d'envoi d'email à $to");
logError("Headers: " . print_r($headers, true));
logError("Contenu: " . $email_content);

// Tentative d'envoi avec mail()
$mail_result = mail($to, $subject, $email_content, implode("\r\n", array_map(
    function ($v, $k) { return "$k: $v"; },
    $headers,
    array_keys($headers)
)));

logError("Résultat de l'envoi avec mail(): " . ($mail_result ? "Succès" : "Échec"));

if ($mail_result) {
    // Tentative d'envoi avec un autre serveur SMTP si disponible
    if (function_exists('mb_send_mail')) {
        $mb_result = mb_send_mail($to, $subject, $email_content, implode("\r\n", array_map(
            function ($v, $k) { return "$k: $v"; },
            $headers,
            array_keys($headers)
        )));
        logError("Résultat de l'envoi avec mb_send_mail(): " . ($mb_result ? "Succès" : "Échec"));
    }
    
    header('Location: /?success=1');
} else {
    logError("Erreur lors de l'envoi de l'email - Erreur PHP: " . error_get_last()['message']);
    header('Location: /?error=send');
}
exit; 