import json
import base64
import csv
import time
from instagram_private_api import Client, ClientError
from instagrapi import Client as InstaClient

# Função para carregar a sessão salva (se existir)
def load_saved_session():
    try:
        with open('credentials.json') as file:
            settings = json.load(file)
            
            if 'cookie' in settings and isinstance(settings['cookie'], str):
                settings['cookie'] = base64.b64decode(settings['cookie'])
            
            return settings
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# Função para salvar a sessão atual
def save_session(api):
    settings = api.settings

    if 'cookie' in settings and isinstance(settings['cookie'], bytes):
        settings['cookie'] = base64.b64encode(settings['cookie']).decode('utf-8')
    
    with open('credentials.json', 'w') as file:
        json.dump(settings, file, indent=4)

# Função para captar solicitações de aprovação
def captar_solicitacoes(api):
    try:
        # Capturar solicitações de seguidores pendentes
        saved_settings = load_saved_session()
        api = Client(username='meowbagsbrand', password='230422Ys@@', settings=saved_settings)
        api.login()
        pending_follow_requests = api.friendships_pending()['users']
        
        with open('solicitacoes.csv', 'a', newline='') as outfile:
            writer = csv.writer(outfile)
            for request in pending_follow_requests:
                user_id = request['pk']
                username = request['username']
                
                # Verificar se o usuário já está no arquivo
                with open('solicitacoes.csv', 'r') as infile:
                    existing_users = [row[0] for row in csv.reader(infile)]
                    
                    if user_id in existing_users:
                        continue

                    else:
                        # Adicionar novo usuário ao arquivo 'solicitacoes.csv'
                        writer.writerow([user_id, username])
                        print(f"Solicitação de: {username} ({user_id}) adicionada ao arquivo.")
                
    except ClientError as e:
        print(f"Erro ao captar solicitações: {e.error_response}")

# Função para enviar DM e mover os usuários para 'usuarios_contatados.csv'
def enviar_dm_e_mover(api, instagrapi_client):
    with open('solicitacoes.csv', 'r') as infile, open('usuarios_contatados.csv', 'a', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        # Ler os usuários já contatados para evitar duplicações
        contatados = set()
        try:
            with open('usuarios_contatados.csv', 'r') as contatados_file:
                contatados_reader = csv.reader(contatados_file)
                for row in contatados_reader:
                    contatados.add(row[0])  # Adiciona o ID do usuário ao conjunto
        except FileNotFoundError:
            pass
        
        # Processar cada solicitação
        for row in reader:
            user_id, username = row

            if user_id in contatados:
                print("Usuário já contatado")
                continue

            try:
                # Enviar mensagem direta (DM) usando o instagrapi
                mensagem = ("Olá, ficamos felizes em ter você em nosso canal interno. "
                            "Você é um dos nossos colaboradores? Responda com 'Sim' ou 'Não'.")
                settingss = instagrapi_client.load_settings('credentials.json')
                instagrapi_client.set_settings(settingss)
                instagrapi_client.login('zzzzz', 'xxxxxx')

                instagrapi_client.direct_send(mensagem, [user_id])
                print(f"Mensagem enviada para {username} ({user_id})")

                # Mover o usuário para o arquivo 'usuarios_contatados.csv'
                writer.writerow([user_id, username])

            except Exception as e:
                print(f"Erro ao enviar DM para {username}: {e}")

    # Após o processamento, esvaziar o arquivo original
    #open('solicitacoes.csv', 'w').close()

# Função para verificar respostas dos usuários
def verificar_respostas(api, instagrapi_client):
    contatados = set()
    try:
        with open('usuarios_contatados.csv', 'r') as contatados_file:
            contatados_reader = csv.reader(contatados_file)
            for row in contatados_reader:
                contatados.add(row[0])  # Adiciona o ID do usuário ao conjunto
    except FileNotFoundError:
        return

    with open('usuarios_contatados.csv', 'r') as infile, open('usuarios_responderam.csv', 'a', newline='') as outfile, open('rejeitados.csv', 'a', newline='') as rejeitados_file, open('colaboradores.csv', 'a', newline='') as colaboradores_file:
        reader = csv.reader(infile)
        responderam_writer = csv.writer(outfile)
        rejeitados_writer = csv.writer(rejeitados_file)
        colaboradores_writer = csv.writer(colaboradores_file)
        temp_file = 'temp_usuarios_contatados.csv'
        
        with open(temp_file, 'w', newline='') as temp_file_out:
            temp_writer = csv.writer(temp_file_out)

            for user_id in contatados:
                try:
                    # Buscar mensagens diretas para cada usuário
                    settingss = instagrapi_client.load_settings('credentials.json')
                    instagrapi_client.set_settings(settingss)
                    instagrapi_client.login('meowbagsbrand', '230422Ys@@')

                    threads = instagrapi_client.direct_threads()
                    for thread in threads:
                        if thread.messages[0].user_id not in contatados:
                            continue

                        messages = instagrapi_client.direct_messages(thread.messages[0].thread_id)
                        for message in messages:
                            if message.user_id == user_id:
                                text = message.text.strip().lower()
                                
                                if text in ['Sim', 's', 'ss', 'sim', 'ssim', 'sS', 'Ss']:
                                    print(f"Usuário {user_id} respondeu 'Sim'.")
                                    instagrapi_client.direct_send("A qual unidade você pertence? E qual o seu gestor?", [user_id])
                                    colaboradores_writer.writerow([user_id])
                                    # Aprovar a solicitação de acesso
                                    break
                                elif text in ['Não', 'nao', 'n', 'não', 'ñ', 'Ñ']:
                                    print(f"Usuário {user_id} respondeu 'Não'.")
                                    resposta_negativa = "Agradecemos o contato, porém este perfil é somente para colaboradores."
                                    instagrapi_client.direct_send(resposta_negativa, [user_id])
                                    rejeitados_writer.writerow([user_id])
                                    break
                            
                            # Se a mensagem foi lida, remova o usuário do arquivo original
                            temp_writer.writerow([user_id, message.text])

                except Exception as e:
                    print(f"Erro ao verificar mensagens para {user_id}: {e}")

    # Substituir o arquivo original pelo temporário
    #with open('usuarios_contatados.csv', 'w', newline='') as outfile:
    #    with open(temp_file, 'r') as infile:
    #        outfile.write(infile.read())

    # Remover o arquivo temporário
    #import os
    #os.remove(temp_file)

def main():
    username = 'uyyyryyyy'
    password = 'xxxxxxxxx'

    saved_settings = load_saved_session()

    try:
        if saved_settings:
            api = Client(username, password, settings=saved_settings)
        else:
            api = Client(username, password)
            save_session(api)
        
        # Inicializar instagrapi
        instagrapi_client = InstaClient()
        settingss = instagrapi_client.load_settings('credentials.json')
        instagrapi_client.set_settings(settingss)
        instagrapi_client.login(username, password)
        
        captar_solicitacoes(api)
        enviar_dm_e_mover(api, instagrapi_client)
        verificar_respostas(api, instagrapi_client)

    except ClientError as e:
        if e.code == 400 and 'checkpoint_challenge_required' in str(e):
            print("Erro de Checkpoint: Por favor, complete o desafio de verificação no Instagram.")
            while True:
                try:
                    print(e.error_response)
                    print("Tentando reconectar...")
                    print("Aguardando verificação manual... tentando novamente em 1 minuto.")
                    time.sleep(30)  # Espera 5 minutos antes de tentar novamente
                    break # Sai do loop se o login for bem-sucedido
                except ClientError as e:
                    print("Falhou")
            # Depois que a verificação for concluída, continue com as funções
            api = Client(username, password)
            save_session(api)
            instagrapi_client = InstaClient()
            instagrapi_client.login(username, password)

            captar_solicitacoes(api)
            enviar_dm_e_mover(api, instagrapi_client)
            verificar_respostas(api, instagrapi_client)
        else:
            print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
