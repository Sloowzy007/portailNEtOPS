/* NetOps - comportements côté navigateur.
 *
 * Confirmation avant une action destructive : ajouter l'attribut
 * data-confirm="Votre question ?" sur un <form> dans le HTML.
 * Si l'utilisateur répond « Annuler », le formulaire n'est pas envoyé.
 */
document.addEventListener("submit", (event) => {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});
