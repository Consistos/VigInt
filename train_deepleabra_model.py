import leabra
import numpy as np
import matplotlib.pyplot as plt
from deep_obj_cat.sims.cemer import cemer_network
from deep_obj_cat.papers.deepredIrn2021.deep_pred_lrn_2021 import DeepPredLrn

# Définir les paramètres du modèle
n_input = 784  # Taille de l'entrée (par exemple, pour une image 28x28)
n_hidden = 500  # Nombre de neurones dans la couche cachée
n_output = 10  # Nombre de classes de sortie

# Créer le réseau en utilisant CEMER
net = cemer_network.Network()

# Ajouter les couches avec DeepPredLrn
input_layer = DeepPredLrn(n_input, name='input')
hidden_layer = DeepPredLrn(n_hidden, name='hidden')
output_layer = DeepPredLrn(n_output, name='output')

net.add_layers([input_layer, hidden_layer, output_layer])

# Connecter les couches
net.connect(input_layer, hidden_layer)
net.connect(hidden_layer, output_layer)

# Fonction pour générer des données d'entraînement synthétiques
def generate_synthetic_data(n_samples):
    X = np.random.rand(n_samples, n_input)
    y = np.random.randint(0, n_output, n_samples)
    return X, y

# Générer des données d'entraînement
n_samples = 1000
X_train, y_train = generate_synthetic_data(n_samples)

# Fonction d'entraînement
def train_model(net, X, y, epochs=10):
    losses = []
    for epoch in range(epochs):
        epoch_loss = 0
        for i in range(len(X)):
            # Définir l'entrée
            input_layer.set_input(X[i])
            
            # Définir la sortie cible
            target = np.zeros(n_output)
            target[y[i]] = 1
            output_layer.set_target(target)
            
            # Exécuter un cycle avec prédiction profonde
            net.deep_pred_cycle()
            
            # Calculer la perte
            loss = output_layer.compute_loss()
            epoch_loss += loss
        
        losses.append(epoch_loss / len(X))
        print(f"Epoch {epoch+1}/{epochs}, Loss: {losses[-1]:.4f}")
    
    return losses

# Entraîner le modèle
losses = train_model(net, X_train, y_train)

# Tracer la courbe de perte
plt.plot(losses)
plt.title('Courbe de perte pendant l\'entraînement')
plt.xlabel('Epochs')
plt.ylabel('Perte')
plt.show()

# Fonction pour tester le modèle sur une nouvelle entrée
def test_model(net, input_data):
    input_layer.set_input(input_data)
    net.deep_pred_cycle()
    return output_layer.get_output()

# Exemple de test
test_input = np.random.rand(n_input)
prediction = test_model(net, test_input)
print("Prédiction pour l'entrée de test:", prediction)
print("Classe prédite:", np.argmax(prediction))

# Sauvegarder le modèle
net.save('deepleabra_model.pkl')
