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

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    logError("Méthode non autorisée: " . $_SERVER['REQUEST_METHOD']);
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

// Récupérer les données POST
$name = $_POST['name'] ?? '';
$email = $_POST['email'] ?? '';
$message = $_POST['message'] ?? '';

logError("Données reçues - Nom: $name, Email: $email");

if (empty($name) || empty($email) || empty($message)) {
    logError("Champs manquants dans la requête");
    http_response_code(400);
    echo json_encode(['error' => 'Missing required fields']);
    exit;
}

$name = filter_var($name, FILTER_SANITIZE_STRING);
$email = filter_var($email, FILTER_SANITIZE_EMAIL);
$message = filter_var($message, FILTER_SANITIZE_STRING);

logError("Données filtrées - Nom: $name, Email: $email");

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    logError("Format d'email invalide: $email");
    http_response_code(400);
    echo json_encode(['error' => 'Invalid email format']);
    exit;
}

$to = "jamilmdk.pro@gmail.com";
$subject = "Nouveau message de contact - Portfolio";
$headers = "From: $email\r\n";
$headers .= "Reply-To: $email\r\n";
$headers .= "X-Mailer: PHP/" . phpversion() . "\r\n";
$headers .= "MIME-Version: 1.0\r\n";
$headers .= "Content-Type: text/plain; charset=UTF-8\r\n";

$email_content = "Nom: " . $name . "\n";
$email_content .= "Email: " . $email . "\n\n";
$email_content .= "Message:\n" . $message;

logError("Tentative d'envoi d'email à $to");
logError("Headers: " . $headers);
logError("Contenu: " . $email_content);

$mail_result = mail($to, $subject, $email_content, $headers);
logError("Résultat de l'envoi: " . ($mail_result ? "Succès" : "Échec"));

if ($mail_result) {
    echo json_encode(['success' => true, 'message' => 'Email sent successfully']);
} else {
    logError("Erreur lors de l'envoi de l'email - Erreur PHP: " . error_get_last()['message']);
    http_response_code(500);
    echo json_encode(['error' => 'Failed to send email']);
} 