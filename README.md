-- Projeto de ITI 2025/26 --

Criação de uma UM Drive. Consegue fazer CRUD (Create, Read, Update, Delete) operações.

Para correr o codigo python: -source /home/henrique/ITI/venv/bin/activate: para entrar no ambiente virtual 
                            -cd umdrive: para entrar na pasta 
                            -python umdrive.py: para iniciar o servidor flask

Enquanto o servidor flask esta a correr abrir outro terminal para correr o cliente

-- Fazer upload de um ficheiro -- (Substitui o caminho (o que esta em "") pelo ficheiro que quiseres enviar. O caminho deve tem de ser o da Maquina Virtual)

curl -F "file=@/home/henrique/teste.txt" http://localhost:5000/api/files
    
    Se o upload correr bem, vais ver algo como:
    {"message":"uploaded","file":"teste.txt"}

-- Listar ficheiros existentes --

curl http://localhost:5000/api/files

-- Fazer download de um ficheiro --

curl -O http://localhost:5000/api/files/teste.txt/download


-- Apagar um ficheiro --

curl -X DELETE http://localhost:5000/api/files/teste.txt

-- Ver/guardar metadados --
  
curl -H "Content-Type: application/json" \
      -d '{"autor":"Henrique","tags":["exemplo"]}' \
      -X POST http://localhost:5000/api/files/teste.txt/metadata

    curl -H "Content-Type: application/json" \
        -d '{"autor":"Henrique","tags":["exemplo"]}' \
        -X POST http://localhost:5000/api/files/teste.txt/metadata
