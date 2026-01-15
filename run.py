from app import create_app    #importa la funzione che crea l'app flask
app = create_app()            #crea un'instanza dell'app usando l'application factory
if __name__ == '__main__':    #controlla se il file è eseguito direttamente
    app.run(debug=True)       #avvia il server flask in modalita debug