pipeline {
    agent {
        kubernetes {
            yamlFile 'k8s/jenkins-slave.yaml'
            defaultContainer 'az-kube' 
        }
    } 

    triggers {
        pollSCM('H/2 * * * *')
    }

    options {
        disableConcurrentBuilds()
        timeout(time: 10)
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {

        DEPLOYMENT_NAME = "fetch-script" 
        GIT_REPO = "github.com/ABC-COVID19/fetchScript.git"
        NAMESPACE_DEV = "icam-dev" 
        NAMESPACE_PROD = "icam-prod" 
        DOCKER_HUB = "docker.icam.org.pt" //Need refactor to dns name
        // SLACK_CHANNEL = '' 
        // SLACK_TEAM_DOMAIN = ''
        // SLACK_TOKEN = credentials('')
        GIT_USER = 'jenkins-icam@protonmail.com'
        GIT_USER_NAME = 'jenkins-icam'
        PROJECT_VERSION = readFile(file: 'version.txt').trim()
        NEW_VERSION = bumpVersion("${PROJECT_VERSION}","patch")

    }

    stages {
        

        stage('Recursive build Check') {
            steps {
                script {
                    if (checkCommit("updated version to")){
                        timeout(time: 10, unit: 'SECONDS') {
                            input 'Recursive Run'
                        }
                    }
                }
            }
        }

        stage('Bump Version on file') {
            when {
                branch "develop"
            }
            steps {
                 sh "echo ${NEW_VERSION} > version.txt"
                 sh "cat version.txt || true"
                 sh "echo The new version will be: ${NEW_VERSION}"
            }
        }

        stage('Build and Test') {
            steps {
                container('python3'){
                    sh "docker build -f Dockerfile -t ${DOCKER_HUB}/${DEPLOYMENT_NAME}:${NEW_VERSION} ."
                }
                    

            }
        }
        stage('Update version on Develop') {
            when {
                branch "develop"
            }
             steps {
                        sh "git config --global user.email '${GIT_USER}'"
                        sh "git config --global user.name '${GIT_USER_NAME}'"
                        sh "git add -A"
                        sh "git commit -m 'updated version to ${NEW_VERSION}'"
                        withCredentials([usernamePassword(credentialsId: 'Jenkins-ICAM2', usernameVariable: 'username', passwordVariable: 'password')]) {
                             sh "git push https://${username}:${password}@${GIT_REPO} HEAD:develop"
                        }
            }
        }

        stage('Merge to Master') {
            when {
                branch "develop"
            }
            steps {
                script{
                    try{
                        timeout(time: 90, unit: 'SECONDS') {
                            input 'Confirm Merge to master?'
                        }

                        sh "git config --global user.email '${GIT_USER}'"
                        sh "git config --global user.name '${GIT_USER_NAME}'"
                        sh "git config http.sslVerify false" //WorkAround
                        sh "git checkout -f origin/master" 
                        sh "git merge --ff ${env.GIT_COMMIT}"


                        withCredentials([usernamePassword(credentialsId: 'Jenkins-ICAM2', usernameVariable: 'username', passwordVariable: 'password')]) {
                            sh "git push https://${username}:${password}@${GIT_REPO} HEAD:master"

                        }
                    }catch(err){
                        sh "echo Skipped by users"
                    }
                }
            }
        }
        
        stage('Deliver to Hub - Deploy to DEV') {
            when {
                branch "develop"
            }
            steps {
                        sh "docker tag ${DOCKER_HUB}/${DEPLOYMENT_NAME}:${NEW_VERSION} ${DOCKER_HUB}/${DEPLOYMENT_NAME}:latest"
                        sh "docker push ${DOCKER_HUB}/${DEPLOYMENT_NAME}:${NEW_VERSION}"
                        sh "docker push ${DOCKER_HUB}/${DEPLOYMENT_NAME}:latest"
                        withCredentials([azureServicePrincipal('Azure_login')]) { 
                                    sh "az login --service-principal -u ${AZURE_CLIENT_ID} -p ${AZURE_CLIENT_SECRET} -t ${AZURE_TENANT_ID}"
                                    sh "az aks get-credentials --name icamch --resource-group icam-ch --overwrite-existing"
                                    sh "kubectl set image deployment ${DEPLOYMENT_NAME} ${DEPLOYMENT_NAME}=${DOCKER_HUB}/${DEPLOYMENT_NAME}:${NEW_VERSION} --record -n ${NAMESPACE_DEV}"
                                }
            }
        }
        stage('Deliver to Hub - Deploy to PROD') {
            when {
                branch "master"
            }
            steps {
                        sh "docker tag ${DOCKER_HUB}/${DEPLOYMENT_NAME}:${NEW_VERSION} ${DOCKER_HUB}/${DEPLOYMENT_NAME}:latest"
                        sh "docker push ${DOCKER_HUB}/${DEPLOYMENT_NAME}:${NEW_VERSION}"
                        sh "docker push ${DOCKER_HUB}/${DEPLOYMENT_NAME}:latest"

                        withCredentials([azureServicePrincipal('Azure_login')]) { 
                                    sh "az login --service-principal -u ${AZURE_CLIENT_ID} -p ${AZURE_CLIENT_SECRET} -t ${AZURE_TENANT_ID}"
                                    sh "az aks get-credentials --name icamch --resource-group icam-ch --overwrite-existing"
                                    sh "kubectl set image deployment ${DEPLOYMENT_NAME} ${DEPLOYMENT_NAME}=${DOCKER_HUB}/${DEPLOYMENT_NAME}:${NEW_VERSION} --record -n ${NAMESPACE_PROD}"
                                }



            }
        }
    }

    post {
        always {
                sh "docker rmi ${DOCKER_HUB}/${DEPLOYMENT_NAME}:${NEW_VERSION} || true "
                sh "docker rmi ${DOCKER_HUB}/${DEPLOYMENT_NAME}:latest || true "
            // notifySlack()
        }
        cleanup {
            cleanWs()
        }
    }
}

/*****************************************
 * To use this function you need to install
 * the Slack Notification Plugin
 ****************************************/

def notifySlack(additionalInfo = '') {
    def colorCode = '#79ae40'
    def status = 'SUCCESS'
    if (currentBuild.result == 'FAILURE') {
        colorCode = '#d34e56'
        status = 'FAILURE'
    }
    def commitText = sh(returnStdout: true, script: 'git show -s --format=format:"*%s*  _by %an_" HEAD').trim()
    def subject = "${env.JOB_NAME} - #${env.BUILD_NUMBER} ${status} (<${env.BUILD_URL}|Open>)"
    def summary = "${subject}\nChanges: ${commitText}\nBranch: ${env.GIT_BRANCH}\n${additionalInfo}"
    slackSend channel: "${env.SLACK_CHANNEL}", color: colorCode, message: summary, teamDomain: "${env.SLACK_TEAM_DOMAIN}", token: "${env.SLACK_TOKEN}"
}

def getLastSprint(branch){
    check = sh(returnStdout: true, script: 'git branch -a | grep sprint | tail -1 | cut -d "/" -f 3')
    return check.contains(branch)
}

def chooseVersion(oldVersion, branch){
    return branch.contains("sprint_") ? bumpVersion(oldVersion,'patch') : 
            branch.contains("develop") ? bumpVersion(oldVersion,'minor') : "NONE"
}

def bumpVersion(oldVersion, arg) {
    //eg: bumpVersion(0.2.3-Snapshot, major) -> 1.0.0-Snapshot 
    def pos = ["major", "minor", "patch"].indexOf(arg)
    def parts = oldVersion.split("-|\\.")
    parts[pos] = Integer.parseInt(parts[pos]) + 1
    for(i = pos + 1; i < 3; i++) parts[i] = 0
    return parts.length == 3 ? parts[0..2].join('.') : [parts[0..2].join('.'), parts[3]].join('-')
}

def checkCommit(message) {
    def commitText = sh(returnStdout: true, script: 'git show -s --format="%s"').trim()
    return commitText.contains(message)
}