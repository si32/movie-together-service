function createParty(event) {
    user_id = document.querySelector('#user_id').value;
    film_id = event.srcElement.id;

    party_creation_message = {
        "film_id": film_id,
        "users_ids": [user_id]
    };

    console.log(JSON.stringify(party_creation_message));

    fetch('http://localhost:8002/party-manager-service/api/v1/broker/party-creation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(party_creation_message)
    })
    .then(response => response.json())
    .then(data => {
        window.location.replace(data['redirect_url']);
        // window.location.replace('http://localhost/party-manager-service/api/v1/stream/06547b75-6593-44c2-b4f8-47b4f0b9e426');
    })
};